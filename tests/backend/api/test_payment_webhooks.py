from __future__ import annotations

import json
from uuid import uuid4

from factories.catalog import (
    create_product_offer,
)
from fastapi.testclient import TestClient
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.domain.payment import (
    PaymentAttemptStatus,
)
from app.main import app
from app.models.order import Order
from app.models.payment import (
    PaymentWebhookEvent,
)
from app.models.user import User
from app.payments.provider import (
    PaymentCompletionResult,
    PaymentStatusResult,
)
from app.payments.registry import (
    PaymentProviderRegistry,
    get_payment_provider_registry,
)
from app.repositories.payment_repository import (
    get_payment_attempt_for_update,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
)
from app.services.payment_service import (
    prepare_payment,
    prepare_payment_attempt,
)

ORDER_REFERENCE = "PAYPALORDERWEBHOOK123"


class FakePayPalWebhookProvider:
    name = "paypal"

    def __init__(
        self,
        *,
        verified: bool = True,
    ) -> None:
        self.verified = verified
        self.verify_calls = []
        self.complete_calls = []
        self.status_calls = []

    def verify_webhook_signature(
        self,
        **kwargs,
    ) -> bool:
        self.verify_calls.append(kwargs)
        return self.verified

    def complete_payment(
        self,
        request,
    ) -> PaymentCompletionResult:
        self.complete_calls.append(request)

        return PaymentCompletionResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=(request.provider_reference),
        )

    def get_payment_status(
        self,
        request,
    ) -> PaymentStatusResult:
        self.status_calls.append(request)

        return PaymentStatusResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=(request.provider_reference),
        )


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "PayPal-Transmission-Id": "TX-BYNET-123",
        "PayPal-Transmission-Time": "2026-08-25T00:00:00Z",
        "PayPal-Transmission-Sig": "signature-value",
        "PayPal-Cert-Url": (
            "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-BYNET"
        ),
        "PayPal-Auth-Algo": "SHA256withRSA",
    }


def _raw_event(
    *,
    event_id: str,
    event_type: str,
    provider_reference: str,
) -> bytes:
    if event_type == "CHECKOUT.ORDER.APPROVED":
        resource = {
            "id": provider_reference,
        }
    else:
        resource = {
            "id": "CAPTUREBYNET123",
            "supplementary_data": {
                "related_ids": {
                    "order_id": provider_reference,
                }
            },
        }

    return json.dumps(
        {
            "id": event_id,
            "event_type": event_type,
            "resource": resource,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _install_provider(
    provider,
) -> None:
    registry = PaymentProviderRegistry()
    registry.register(provider)

    app.dependency_overrides[get_payment_provider_registry] = lambda: registry


def _remove_provider_override() -> None:
    app.dependency_overrides.pop(
        get_payment_provider_registry,
        None,
    )


def _create_pending_attempt(
    db: Session,
    *,
    provider_reference: str,
):
    suffix = uuid4().hex

    user = User(
        email=(f"webhook-{suffix}@example.com"),
        password_hash=hash_password("webhook-test-credential"),
        is_active=True,
    )

    db.add(user)
    db.flush()

    _, offer = create_product_offer(
        db,
        slug=f"webhook-{suffix}",
        price_cents=1234,
        stock_quantity=3,
    )

    db.commit()

    order = create_pending_order(
        db,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=1,
                )
            ]
        ),
        user_id=user.id,
        idempotency_key=(f"webhook-order-{suffix}"),
    )

    payment = prepare_payment(
        db,
        order_id=order.id,
        user_id=user.id,
    )

    attempt = prepare_payment_attempt(
        db,
        payment_id=payment.id,
        user_id=user.id,
        provider="paypal",
        idempotency_key=(f"webhook-attempt-{suffix}"),
    )

    locked = get_payment_attempt_for_update(
        db,
        attempt_id=attempt.id,
    )

    assert locked is not None

    locked.status = PaymentAttemptStatus.PENDING.value
    locked.provider_reference = provider_reference

    db.commit()

    return order.id, attempt.id


def test_paypal_webhook_requires_all_signature_headers(
    client: TestClient,
):
    provider = FakePayPalWebhookProvider()
    _install_provider(provider)

    headers = _headers()
    headers.pop("PayPal-Cert-Url")

    try:
        response = client.post(
            "/api/v1/webhooks/paypal",
            content=_raw_event(
                event_id="WH-MISSING-HEADER",
                event_type=("CHECKOUT.ORDER.APPROVED"),
                provider_reference=(ORDER_REFERENCE),
            ),
            headers=headers,
        )
    finally:
        _remove_provider_override()

    assert response.status_code == 400
    assert provider.verify_calls == []


def test_paypal_webhook_rejects_invalid_signature(
    client: TestClient,
    db_session: Session,
):
    provider = FakePayPalWebhookProvider(verified=False)

    _install_provider(provider)

    event_id = "WH-BAD-SIGNATURE"

    try:
        response = client.post(
            "/api/v1/webhooks/paypal",
            content=_raw_event(
                event_id=event_id,
                event_type=("CHECKOUT.ORDER.APPROVED"),
                provider_reference=(ORDER_REFERENCE),
            ),
            headers=_headers(),
        )
    finally:
        _remove_provider_override()

    assert response.status_code == 401
    assert len(provider.verify_calls) == 1

    stored = db_session.scalar(
        select(func.count())
        .select_from(PaymentWebhookEvent)
        .where(PaymentWebhookEvent.provider_event_id == event_id)
    )

    assert stored == 0


def test_paypal_approved_webhook_captures_and_deduplicates(
    client: TestClient,
    db_session: Session,
):
    order_id, attempt_id = _create_pending_attempt(
        db_session,
        provider_reference=(ORDER_REFERENCE),
    )

    provider = FakePayPalWebhookProvider()
    _install_provider(provider)

    raw_body = _raw_event(
        event_id="WH-APPROVED-ENDPOINT",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference=ORDER_REFERENCE,
    )

    try:
        first = client.post(
            "/api/v1/webhooks/paypal",
            content=raw_body,
            headers=_headers(),
        )

        second = client.post(
            "/api/v1/webhooks/paypal",
            content=raw_body,
            headers=_headers(),
        )
    finally:
        _remove_provider_override()

    assert first.status_code == 200
    assert second.status_code == 200

    # Every delivery is independently
    # authenticated before deduplication.
    assert len(provider.verify_calls) == 2

    # But financial completion happens once.
    assert len(provider.complete_calls) == 1

    assert provider.verify_calls[0]["raw_webhook_event"] == raw_body

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    assert order is not None
    assert order.status == "paid"

    event = db_session.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider_event_id == "WH-APPROVED-ENDPOINT"
        )
    )

    assert event is not None
    assert event.processed_at is not None
    assert event.payment_attempt_id == attempt_id


def test_paypal_capture_webhook_refreshes_provider_status(
    client: TestClient,
    db_session: Session,
):
    order_id, _ = _create_pending_attempt(
        db_session,
        provider_reference=(ORDER_REFERENCE),
    )

    provider = FakePayPalWebhookProvider()
    _install_provider(provider)

    try:
        response = client.post(
            "/api/v1/webhooks/paypal",
            content=_raw_event(
                event_id=("WH-CAPTURE-ENDPOINT"),
                event_type=("PAYMENT.CAPTURE.COMPLETED"),
                provider_reference=(ORDER_REFERENCE),
            ),
            headers=_headers(),
        )
    finally:
        _remove_provider_override()

    assert response.status_code == 200
    assert provider.complete_calls == []
    assert len(provider.status_calls) == 1

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    assert order is not None
    assert order.status == "paid"


def test_paypal_unknown_reference_is_retryable(
    client: TestClient,
    db_session: Session,
):
    provider = FakePayPalWebhookProvider()
    _install_provider(provider)

    event_id = "WH-UNKNOWN-REFERENCE"

    try:
        response = client.post(
            "/api/v1/webhooks/paypal",
            content=_raw_event(
                event_id=event_id,
                event_type=("CHECKOUT.ORDER.APPROVED"),
                provider_reference=("UNKNOWNPAYPALORDER"),
            ),
            headers=_headers(),
        )
    finally:
        _remove_provider_override()

    assert response.status_code == 503
    assert response.headers.get("retry-after") == "5"

    event = db_session.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider_event_id == event_id
        )
    )

    assert event is not None
    assert event.processed_at is None
    assert event.processing_token is None
    assert event.processing_started_at is None


def test_paypal_webhook_in_progress_is_retryable(
    client: TestClient,
    db_session: Session,
):
    from app.services.payment_webhook_service import (
        PaymentWebhookClaimState,
        claim_payment_webhook_event,
    )

    event_id = "WH-IN-PROGRESS-ENDPOINT"

    claim = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id=event_id,
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference=(ORDER_REFERENCE),
    )

    assert claim.state == PaymentWebhookClaimState.CLAIMED
    assert claim.processing_token is not None

    provider = FakePayPalWebhookProvider()

    _install_provider(provider)

    try:
        response = client.post(
            "/api/v1/webhooks/paypal",
            content=_raw_event(
                event_id=event_id,
                event_type=("CHECKOUT.ORDER.APPROVED"),
                provider_reference=(ORDER_REFERENCE),
            ),
            headers=_headers(),
        )
    finally:
        _remove_provider_override()

    assert response.status_code == 503

    assert response.headers.get("retry-after") == "5"

    # Duplicate deliveries are still
    # authenticated.
    assert len(provider.verify_calls) == 1

    # But an active lease blocks financial
    # work by the duplicate worker.
    assert provider.complete_calls == []
    assert provider.status_calls == []
