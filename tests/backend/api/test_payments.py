from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from factories.catalog import create_product_offer
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment


def _credential() -> str:
    return "Strong-payment-api-test-credential-2026!"


def _authenticate(
    client: TestClient,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": (f"payment-api-{uuid4().hex}@example.com"),
            "password": _credential(),
        },
    )

    assert response.status_code == 201

    return response.json()


def _create_order(
    client: TestClient,
    db_session: Session,
    *,
    price_cents: int = 2500,
    currency: str = "EUR",
    quantity: int = 1,
) -> dict[str, object]:
    _, offer = create_product_offer(
        db_session,
        slug=(f"api-payment-offer-{uuid4().hex}"),
        price_cents=price_cents,
        currency=currency,
        stock_quantity=20,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        headers={
            "Idempotency-Key": (f"payment-order-{uuid4().hex}"),
        },
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": quantity,
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()


def test_prepare_payment_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post(
        "/api/v1/payments",
        json={
            "order_id": str(uuid4()),
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
        }
    }


def test_prepare_payment_for_owned_order(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    order = _create_order(
        client,
        db_session,
        price_cents=3250,
        quantity=2,
    )

    response = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["order_id"] == order["id"]
    assert payload["status"] == "pending"
    assert payload["amount_cents"] == 6500
    assert payload["currency"] == "EUR"

    payment = db_session.scalar(
        select(Payment).where(Payment.id == UUID(payload["id"]))
    )

    assert payment is not None
    assert payment.order_id == UUID(order["id"])
    assert payment.amount_cents == 6500
    assert payment.currency == "EUR"


def test_prepare_payment_is_idempotent_per_order(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    order = _create_order(
        client,
        db_session,
    )

    first = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    second = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert second.json()["id"] == first.json()["id"]

    payments = list(
        db_session.scalars(
            select(Payment).where(Payment.order_id == UUID(order["id"]))
        ).all()
    )

    assert len(payments) == 1


def test_prepare_payment_hides_other_users_orders(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    owned_order = _create_order(
        client,
        db_session,
    )

    client.cookies.clear()

    _authenticate(client)

    forbidden = client.post(
        "/api/v1/payments",
        json={
            "order_id": owned_order["id"],
        },
    )

    missing = client.post(
        "/api/v1/payments",
        json={
            "order_id": str(uuid4()),
        },
    )

    assert forbidden.status_code == 404
    assert missing.status_code == 404

    expected = {
        "detail": {
            "code": ("payment_order_unavailable"),
        }
    }

    assert forbidden.json() == expected
    assert missing.json() == expected


def test_prepare_payment_rejects_expired_reservation(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    created = _create_order(
        client,
        db_session,
    )

    order = db_session.get(
        Order,
        UUID(created["id"]),
    )

    assert order is not None

    order.reservation_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    db_session.commit()

    response = client.post(
        "/api/v1/payments",
        json={
            "order_id": created["id"],
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": {
            "code": "order_not_payable",
            "reason": "reservation_expired",
        }
    }

    payment = db_session.scalar(
        select(Payment).where(Payment.order_id == UUID(created["id"]))
    )

    assert payment is None


def test_prepare_payment_rejects_client_amount_and_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    order = _create_order(
        client,
        db_session,
        price_cents=4100,
        currency="EUR",
        quantity=3,
    )

    tampered = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
            "amount_cents": 1,
            "currency": "USD",
        },
    )

    assert tampered.status_code == 422

    payment_before_valid_request = db_session.scalar(
        select(Payment).where(Payment.order_id == UUID(order["id"]))
    )

    assert payment_before_valid_request is None

    valid = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert valid.status_code == 200

    payload = valid.json()

    # Payment snapshot is derived only from
    # the authoritative Order.
    assert payload["amount_cents"] == 12300
    assert payload["currency"] == "EUR"


class RecordingPaymentProvider:
    name = "fake"

    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.calls = []

    def initiate_payment(
        self,
        request,
    ):
        from app.domain.payment import (
            PaymentAttemptStatus,
        )
        from app.payments.provider import (
            PaymentInitiationResult,
        )

        self.calls.append(request)

        if self.fail:
            raise TimeoutError("simulated provider timeout")

        return PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference=(f"fake-{request.attempt_id}"),
            approval_url=("https://example.invalid/pay"),
        )

    def get_payment_status(
        self,
        request,
    ):
        raise NotImplementedError


def _provider_registry(
    provider: RecordingPaymentProvider,
):
    from app.payments.registry import (
        PaymentProviderRegistry,
    )

    registry = PaymentProviderRegistry()
    registry.register(provider)

    return registry


def test_payment_initiation_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post(
        f"/api/v1/payments/{uuid4()}/initiate",
        headers={
            "Idempotency-Key": (f"attempt-{uuid4().hex}"),
        },
        json={
            "provider": "fake",
        },
    )

    assert response.status_code == 401


def test_payment_initiation_uses_authoritative_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    order = _create_order(
        client,
        db_session,
        price_cents=2750,
        quantity=2,
    )

    payment_response = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert payment_response.status_code == 200

    provider = RecordingPaymentProvider()

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/{payment_response.json()['id']}/initiate"),
            headers={
                "Idempotency-Key": (f"attempt-{uuid4().hex}"),
            },
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "pending"
    assert payload["approval_url"] == ("https://example.invalid/pay")

    assert len(provider.calls) == 1

    request = provider.calls[0]

    assert request.amount_cents == 5500
    assert request.currency == "EUR"
    assert str(request.order_id) == order["id"]


def test_payment_initiation_retry_does_not_call_provider_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    order = _create_order(
        client,
        db_session,
    )

    prepared = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert prepared.status_code == 200

    provider = RecordingPaymentProvider()

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    key = f"attempt-{uuid4().hex}"

    try:
        first = client.post(
            (f"/api/v1/payments/{prepared.json()['id']}/initiate"),
            headers={
                "Idempotency-Key": key,
            },
            json={
                "provider": "fake",
            },
        )

        second = client.post(
            (f"/api/v1/payments/{prepared.json()['id']}/initiate"),
            headers={
                "Idempotency-Key": key,
            },
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["attempt_id"] == second.json()["attempt_id"]

    assert len(provider.calls) == 1


def test_payment_initiation_hides_other_users_payment(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    order = _create_order(
        client,
        db_session,
    )

    prepared = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert prepared.status_code == 200

    payment_id = prepared.json()["id"]

    client.cookies.clear()
    _authenticate(client)

    provider = RecordingPaymentProvider()

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        forbidden = client.post(
            (f"/api/v1/payments/{payment_id}/initiate"),
            headers={
                "Idempotency-Key": (f"attempt-{uuid4().hex}"),
            },
            json={
                "provider": "fake",
            },
        )

        missing = client.post(
            (f"/api/v1/payments/{uuid4()}/initiate"),
            headers={
                "Idempotency-Key": (f"attempt-{uuid4().hex}"),
            },
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert forbidden.status_code == 404
    assert missing.status_code == 404
    assert forbidden.json() == missing.json()

    assert forbidden.json() == {
        "detail": {
            "code": "payment_unavailable",
        }
    }


def test_payment_initiation_rejects_unknown_provider(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    order = _create_order(
        client,
        db_session,
    )

    prepared = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert prepared.status_code == 200

    response = client.post(
        (f"/api/v1/payments/{prepared.json()['id']}/initiate"),
        headers={
            "Idempotency-Key": (f"attempt-{uuid4().hex}"),
        },
        json={
            "provider": "unknown",
        },
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": {
            "code": ("unsupported_payment_provider"),
        }
    }


def test_payment_initiation_maps_provider_timeout_to_503(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    order = _create_order(
        client,
        db_session,
    )

    prepared = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert prepared.status_code == 200

    provider = RecordingPaymentProvider(
        fail=True,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/{prepared.json()['id']}/initiate"),
            headers={
                "Idempotency-Key": (f"attempt-{uuid4().hex}"),
            },
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": {
            "code": ("payment_provider_unavailable"),
        }
    }

    assert len(provider.calls) == 1


class CompletingPaymentProvider(RecordingPaymentProvider):
    def __init__(
        self,
        *,
        fail_completion: bool = False,
    ) -> None:
        super().__init__()
        self.fail_completion = fail_completion
        self.completion_calls = []

    def complete_payment(
        self,
        request,
    ):
        from app.domain.payment import (
            PaymentAttemptStatus,
        )
        from app.payments.provider import (
            PaymentCompletionResult,
        )

        self.completion_calls.append(request)

        if self.fail_completion:
            raise TimeoutError("simulated completion timeout")

        return PaymentCompletionResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=(request.provider_reference),
        )


def _prepare_pending_attempt_via_api(
    client: TestClient,
    db_session: Session,
    *,
    provider: RecordingPaymentProvider,
) -> tuple[
    dict[str, object],
    dict[str, object],
]:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    order = _create_order(
        client,
        db_session,
        price_cents=3100,
        quantity=2,
    )

    prepared = client.post(
        "/api/v1/payments",
        json={
            "order_id": order["id"],
        },
    )

    assert prepared.status_code == 200

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        initiated = client.post(
            (f"/api/v1/payments/{prepared.json()['id']}/initiate"),
            headers={
                "Idempotency-Key": (f"attempt-{uuid4().hex}"),
            },
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert initiated.status_code == 200
    assert initiated.json()["status"] == ("pending")

    return order, initiated.json()


def test_payment_completion_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post(
        (f"/api/v1/payments/attempts/{uuid4()}/complete"),
        json={
            "provider": "fake",
        },
    )

    assert response.status_code == 401


def test_payment_completion_marks_order_paid(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = CompletingPaymentProvider()

    order, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/complete"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 200
    assert response.json()["status"] == ("succeeded")

    assert len(provider.completion_calls) == 1

    completion_request = provider.completion_calls[0]

    assert completion_request.amount_cents == 6200
    assert completion_request.currency == "EUR"

    db_session.expire_all()

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    assert stored_order is not None
    assert stored_order.status == "paid"

    payment = db_session.scalar(
        select(Payment).where(Payment.order_id == UUID(order["id"]))
    )

    assert payment is not None
    assert payment.status == "succeeded"


def test_payment_completion_allows_late_provider_success(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = CompletingPaymentProvider()

    order, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    assert stored_order is not None

    stored_order.reservation_expires_at = datetime.now(UTC) - timedelta(hours=1)

    db_session.commit()

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/complete"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 200
    assert response.json()["status"] == ("succeeded")

    db_session.expire_all()

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    assert stored_order is not None
    assert stored_order.status == "paid"


def test_payment_completion_retry_does_not_call_provider_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = CompletingPaymentProvider()

    _, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        first = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/complete"),
            json={
                "provider": "fake",
            },
        )

        second = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/complete"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["attempt_id"] == second.json()["attempt_id"]

    assert first.json()["status"] == second.json()["status"] == "succeeded"

    assert len(provider.completion_calls) == 1


class ReconcilingPaymentProvider(CompletingPaymentProvider):
    def __init__(
        self,
        *,
        fail_status: bool = False,
    ) -> None:
        super().__init__()
        self.fail_status = fail_status
        self.status_calls = []

    def get_payment_status(
        self,
        request,
    ):
        from app.domain.payment import (
            PaymentAttemptStatus,
        )
        from app.payments.provider import (
            PaymentStatusResult,
        )

        self.status_calls.append(request)

        if self.fail_status:
            raise TimeoutError("simulated status timeout")

        return PaymentStatusResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=(request.provider_reference),
        )


def test_payment_status_refresh_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post(
        (f"/api/v1/payments/attempts/{uuid4()}/refresh"),
        json={
            "provider": "fake",
        },
    )

    assert response.status_code == 401


def test_payment_status_refresh_marks_order_paid(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = ReconcilingPaymentProvider()

    order, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 200

    payload = response.json()

    assert payload["order_id"] == order["id"]
    assert payload["order_number"] == order["order_number"]
    assert response.json()["status"] == ("succeeded")

    assert len(provider.status_calls) == 1

    db_session.expire_all()

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    payment = db_session.scalar(
        select(Payment).where(Payment.order_id == UUID(order["id"]))
    )

    assert stored_order is not None
    assert payment is not None

    assert stored_order.status == "paid"
    assert payment.status == "succeeded"


def test_payment_status_refresh_allows_late_success(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = ReconcilingPaymentProvider()

    order, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    assert stored_order is not None

    stored_order.reservation_expires_at = datetime.now(UTC) - timedelta(hours=1)

    db_session.commit()

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 200
    assert response.json()["status"] == ("succeeded")

    db_session.expire_all()

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    assert stored_order is not None
    assert stored_order.status == "paid"


def test_payment_status_refresh_hides_other_users_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = ReconcilingPaymentProvider()

    _, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    client.cookies.clear()
    _authenticate(client)

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        forbidden = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )

        missing = client.post(
            (f"/api/v1/payments/attempts/{uuid4()}/refresh"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert forbidden.status_code == 404
    assert missing.status_code == 404

    assert forbidden.json() == missing.json()

    assert forbidden.json() == {
        "detail": {
            "code": ("payment_attempt_unavailable"),
        }
    }

    # Ownership must be checked before any
    # external provider status call.
    assert provider.status_calls == []


def test_payment_status_terminal_retry_does_not_call_provider_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = ReconcilingPaymentProvider()

    _, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        first = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )

        second = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["status"] == second.json()["status"] == "succeeded"

    assert len(provider.status_calls) == 1


def test_payment_status_timeout_maps_to_503_without_state_change(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app
    from app.models.payment import (
        PaymentAttempt,
    )
    from app.payments.registry import (
        get_payment_provider_registry,
    )

    _authenticate(client)

    provider = ReconcilingPaymentProvider(
        fail_status=True,
    )

    order, initiated = _prepare_pending_attempt_via_api(
        client,
        db_session,
        provider=provider,
    )

    app.dependency_overrides[get_payment_provider_registry] = lambda: (
        _provider_registry(provider)
    )

    try:
        response = client.post(
            (f"/api/v1/payments/attempts/{initiated['attempt_id']}/refresh"),
            json={
                "provider": "fake",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_payment_provider_registry,
            None,
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": {
            "code": ("payment_provider_unavailable"),
        }
    }

    db_session.expire_all()

    stored_order = db_session.get(
        Order,
        UUID(order["id"]),
    )

    attempt = db_session.get(
        PaymentAttempt,
        UUID(initiated["attempt_id"]),
    )

    assert stored_order is not None
    assert attempt is not None

    assert stored_order.status == "pending"
    assert attempt.status == "pending"
