from datetime import timedelta
from uuid import uuid4

import pytest
from factories.catalog import create_product_offer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_security import hash_password
from app.domain.order_event import (
    OrderEventSource,
    OrderEventType,
)
from app.domain.payment import (
    PaymentAttemptStatus,
)
from app.domain.payment_errors import (
    PaymentProviderResultConflictError,
    PaymentProviderUnavailableError,
)
from app.models.order import Order
from app.models.payment import (
    Payment,
    PaymentAttempt,
)
from app.models.product_offer import ProductOffer
from app.models.user import User
from app.payments.orchestrator import (
    initiate_payment,
    refresh_payment_status,
)
from app.payments.provider import (
    PaymentInitiationRequest,
    PaymentInitiationResult,
    PaymentStatusRequest,
    PaymentStatusResult,
)
from app.repositories.order_event_repository import (
    list_order_events,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
    expire_due_pending_orders,
)
from app.services.payment_service import (
    prepare_payment,
    reconcile_provider_status,
)

TEST_CREDENTIAL_HASH = hash_password("payment-orchestrator-test-credential")


def _create_payment(
    db: Session,
) -> tuple:
    suffix = uuid4().hex

    user = User(
        email=(f"payment-orchestrator-{suffix}@example.com"),
        password_hash=(TEST_CREDENTIAL_HASH),
        is_active=True,
    )

    db.add(user)
    db.flush()

    _, offer = create_product_offer(
        db,
        slug=(f"payment-orchestrator-{suffix}"),
        price_cents=2450,
        currency="EUR",
        stock_quantity=5,
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
        idempotency_key=(f"order-{uuid4().hex}"),
    )

    payment = prepare_payment(
        db,
        order_id=order.id,
        user_id=user.id,
    )

    return (
        order.id,
        user.id,
        payment.id,
    )


class RecordingProvider:
    name = "fake"

    def __init__(
        self,
        db: Session,
        result: PaymentInitiationResult,
    ) -> None:
        self.db = db
        self.result = result
        self.calls: list[PaymentInitiationRequest] = []

    def initiate_payment(
        self,
        request: PaymentInitiationRequest,
    ) -> PaymentInitiationResult:
        # This is the critical architecture
        # invariant: provider network I/O must
        # never happen inside a DB transaction.
        assert not self.db.in_transaction()

        self.calls.append(request)

        return self.result


class RecordingStatusProvider:
    name = "fake"

    def __init__(
        self,
        db: Session,
        result: PaymentStatusResult,
    ) -> None:
        self.db = db
        self.result = result
        self.calls: list[PaymentStatusRequest] = []

    def get_payment_status(
        self,
        request: PaymentStatusRequest,
    ) -> PaymentStatusResult:
        # Provider status network I/O must also
        # happen outside any DB transaction.
        assert not self.db.in_transaction()

        self.calls.append(request)

        return self.result


class TimeoutThenSuccessStatusProvider:
    name = "fake"

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db
        self.calls: list[PaymentStatusRequest] = []
        self.timed_out = False

    def get_payment_status(
        self,
        request: PaymentStatusRequest,
    ) -> PaymentStatusResult:
        assert not self.db.in_transaction()

        self.calls.append(request)

        if not self.timed_out:
            self.timed_out = True
            raise TimeoutError("simulated status timeout")

        return PaymentStatusResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=(request.provider_reference),
        )


class TimeoutThenPendingProvider:
    name = "fake-timeout"

    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db
        self.call_count = 0
        self.external_creations = 0
        self.references: dict[
            object,
            str,
        ] = {}
        self.timed_out: set[object] = set()

    def initiate_payment(
        self,
        request: PaymentInitiationRequest,
    ) -> PaymentInitiationResult:
        assert not self.db.in_transaction()

        self.call_count += 1

        reference = self.references.get(request.attempt_id)

        if reference is None:
            reference = f"fake-provider-{request.attempt_id}"

            self.references[request.attempt_id] = reference

            self.external_creations += 1

        if request.attempt_id not in self.timed_out:
            self.timed_out.add(request.attempt_id)

            # Simulates:
            # provider accepted request,
            # but client never received response.
            raise TimeoutError("simulated provider timeout")

        return PaymentInitiationResult(
            status=(PaymentAttemptStatus.PENDING),
            provider_reference=reference,
            approval_url=("https://example.invalid/approve"),
        )


def test_provider_call_runs_without_database_transaction(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=(PaymentAttemptStatus.PENDING),
            provider_reference=("fake-reference-1"),
            approval_url=("https://example.invalid/approve/1"),
        ),
    )

    key = f"attempt-{uuid4().hex}"

    outcome = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=key,
    )

    assert len(provider.calls) == 1

    request = provider.calls[0]

    assert request.payment_id == payment_id
    assert request.order_id == order_id

    assert outcome.status == PaymentAttemptStatus.PENDING

    assert outcome.provider_reference == "fake-reference-1"

    assert outcome.approval_url == ("https://example.invalid/approve/1")

    # A retry after a known provider result
    # must return persisted data without
    # another external call.
    repeated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=key,
    )

    assert len(provider.calls) == 1

    assert repeated.attempt_id == outcome.attempt_id

    assert repeated.provider_reference == outcome.provider_reference


def test_timeout_retry_reuses_same_attempt_identity(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = TimeoutThenPendingProvider(db_session)

    key = f"attempt-{uuid4().hex}"

    with pytest.raises(PaymentProviderUnavailableError):
        initiate_payment(
            db_session,
            payment_id=payment_id,
            user_id=user_id,
            provider=provider,
            idempotency_key=key,
        )

    attempt = db_session.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.payment_id == payment_id,
            PaymentAttempt.idempotency_key == key,
        )
    )

    assert attempt is not None

    first_attempt_id = attempt.id

    # Ambiguous timeout must not be marked
    # FAILED because provider may already
    # have created the payment externally.
    assert attempt.status == PaymentAttemptStatus.CREATED
    assert attempt.provider_reference is None

    order = db_session.get(
        Order,
        order_id,
    )

    assert order is not None

    # The provider outcome is externally
    # ambiguous, so the unresolved CREATED
    # attempt must protect the reservation.
    expiry_time = order.reservation_expires_at + timedelta(seconds=1)

    offer_id = order.items[0].offer_id

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=expiry_time,
    )

    assert expired_count == 0

    persisted_order_status = db_session.scalar(
        select(Order.status).where(Order.id == order_id)
    )

    stock_quantity = db_session.scalar(
        select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
    )

    assert persisted_order_status == "pending"
    assert stock_quantity == 4

    outcome = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=key,
    )

    assert outcome.attempt_id == first_attempt_id

    assert provider.call_count == 2

    # The fake provider uses attempt_id as its
    # external idempotency identity, proving
    # retry did not create a second charge/session.
    assert provider.external_creations == 1

    assert outcome.status == PaymentAttemptStatus.PENDING


def test_successful_provider_result_marks_order_paid(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=(PaymentAttemptStatus.SUCCEEDED),
            provider_reference=("fake-success-1"),
        ),
    )

    outcome = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    assert outcome.status == PaymentAttemptStatus.SUCCEEDED

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        outcome.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    assert order.status == "paid"
    assert payment.status == "succeeded"
    assert attempt.status == "succeeded"

    events = list_order_events(
        db_session,
        order_id=order_id,
    )

    event = events[-1]

    assert event.event_type == OrderEventType.ORDER_STATUS_CHANGED

    assert event.source == OrderEventSource.PAYMENT_SERVICE

    assert event.event_data == {
        "from_status": "pending",
        "to_status": "paid",
        "payment_id": str(payment_id),
        "payment_attempt_id": str(outcome.attempt_id),
    }


@pytest.mark.parametrize(
    ("provider_status", "failure_code"),
    [
        (
            PaymentAttemptStatus.FAILED,
            "provider_declined",
        ),
        (
            PaymentAttemptStatus.CANCELLED,
            None,
        ),
    ],
)
def test_terminal_unsuccessful_provider_result_releases_reservation_hold(
    db_session: Session,
    provider_status: PaymentAttemptStatus,
    failure_code: str | None,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=provider_status,
            provider_reference=None,
            failure_code=failure_code,
        ),
    )

    outcome = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    assert outcome.status == provider_status
    assert outcome.failure_code == failure_code

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        outcome.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    # One failed/cancelled attempt does not
    # make the aggregate Payment terminal;
    # another attempt may still be created.
    assert order.status == "pending"
    assert payment.status == "pending"
    assert attempt.status == provider_status

    offer_id = order.items[0].offer_id

    expiry_time = order.reservation_expires_at + timedelta(seconds=1)

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=expiry_time,
    )

    assert expired_count == 1

    db_session.expire_all()

    expired_order = db_session.get(
        Order,
        order_id,
    )

    stock_quantity = db_session.scalar(
        select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
    )

    assert expired_order is not None
    assert expired_order.status == "expired"

    # Initial stock was 5; checkout reserved 1.
    assert stock_quantity == 5


def test_ambiguous_timeout_blocks_expiry_even_after_local_grace(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = TimeoutThenPendingProvider(db_session)

    key = f"attempt-{uuid4().hex}"

    with pytest.raises(PaymentProviderUnavailableError):
        initiate_payment(
            db_session,
            payment_id=payment_id,
            user_id=user_id,
            provider=provider,
            idempotency_key=key,
        )

    attempt = db_session.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.payment_id == payment_id,
            PaymentAttempt.idempotency_key == key,
        )
    )

    order = db_session.get(
        Order,
        order_id,
    )

    assert attempt is not None
    assert order is not None

    assert attempt.status == PaymentAttemptStatus.CREATED

    offer_id = order.items[0].offer_id

    # Local wall-clock time may be far beyond
    # the reservation deadline. CREATED is
    # still externally ambiguous and must
    # protect inventory until reconciled.
    expiry_time = order.reservation_expires_at + timedelta(hours=1)

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=expiry_time,
    )

    assert expired_count == 0

    db_session.expire_all()

    persisted_order = db_session.get(
        Order,
        order_id,
    )

    stock_quantity = db_session.scalar(
        select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
    )

    assert persisted_order is not None
    assert persisted_order.status == "pending"

    # Initial stock 5; checkout reserved 1.
    assert stock_quantity == 4


def test_pending_provider_attempt_blocks_expiry_after_reservation_deadline(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference="pending-expiry-guard",
            approval_url=("https://example.invalid/pending-expiry-guard"),
        ),
    )

    outcome = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    assert outcome.status == PaymentAttemptStatus.PENDING

    order = db_session.get(
        Order,
        order_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        outcome.attempt_id,
    )

    assert order is not None
    assert attempt is not None

    assert attempt.status == PaymentAttemptStatus.PENDING

    offer_id = order.items[0].offer_id

    # Deliberately far beyond the ordinary
    # reservation deadline. Protection comes
    # from the unresolved PaymentAttempt.
    expiry_time = order.reservation_expires_at + timedelta(hours=1)

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=expiry_time,
    )

    assert expired_count == 0

    db_session.expire_all()

    persisted_order = db_session.get(
        Order,
        order_id,
    )

    stock_quantity = db_session.scalar(
        select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
    )

    assert persisted_order is not None
    assert persisted_order.status == "pending"

    # Initial stock 5; checkout reserved 1.
    assert stock_quantity == 4


def test_pending_status_refresh_remains_pending(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference="status-pending-1",
            approval_url=("https://example.invalid/status-pending-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    assert initiated.status == PaymentAttemptStatus.PENDING

    status_provider = RecordingStatusProvider(
        db_session,
        PaymentStatusResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference=("status-pending-1"),
        ),
    )

    outcome = refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=status_provider,
    )

    assert len(status_provider.calls) == 1

    request = status_provider.calls[0]

    assert request.attempt_id == (initiated.attempt_id)

    assert request.payment_id == payment_id
    assert request.order_id == order_id
    assert request.provider_reference == "status-pending-1"

    assert outcome.status == PaymentAttemptStatus.PENDING

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    assert order.status == "pending"
    assert payment.status == "pending"
    assert attempt.status == "pending"


def test_pending_status_refresh_can_mark_order_paid_after_reservation_deadline(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference="late-success-1",
            approval_url=("https://example.invalid/late-success-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    order = db_session.get(
        Order,
        order_id,
    )

    assert order is not None

    # Simulate customer/provider confirmation
    # arriving after the original reservation
    # deadline. The unresolved PENDING attempt
    # has kept inventory protected.
    order.reservation_expires_at = order.reservation_expires_at - timedelta(hours=1)

    db_session.commit()

    status_provider = RecordingStatusProvider(
        db_session,
        PaymentStatusResult(
            status=PaymentAttemptStatus.SUCCEEDED,
            provider_reference="late-success-1",
        ),
    )

    outcome = refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=status_provider,
    )

    assert outcome.status == PaymentAttemptStatus.SUCCEEDED

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    assert order.status == "paid"
    assert payment.status == "succeeded"
    assert attempt.status == "succeeded"

    events = list_order_events(
        db_session,
        order_id=order_id,
    )

    event = events[-1]

    assert event.event_type == OrderEventType.ORDER_STATUS_CHANGED

    assert event.source == OrderEventSource.PAYMENT_SERVICE

    assert event.event_data == {
        "from_status": "pending",
        "to_status": "paid",
        "payment_id": str(payment_id),
        "payment_attempt_id": str(initiated.attempt_id),
    }


@pytest.mark.parametrize(
    "terminal_status",
    [
        PaymentAttemptStatus.FAILED,
        PaymentAttemptStatus.CANCELLED,
    ],
)
def test_pending_status_terminal_failure_allows_order_expiry(
    db_session: Session,
    terminal_status: PaymentAttemptStatus,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference=("status-terminal-1"),
            approval_url=("https://example.invalid/status-terminal-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    failure_code = (
        "provider_declined" if terminal_status == PaymentAttemptStatus.FAILED else None
    )

    status_provider = RecordingStatusProvider(
        db_session,
        PaymentStatusResult(
            status=terminal_status,
            provider_reference=("status-terminal-1"),
            failure_code=failure_code,
        ),
    )

    outcome = refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=status_provider,
    )

    assert outcome.status == terminal_status
    assert outcome.failure_code == failure_code

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    assert order.status == "pending"
    assert payment.status == "pending"
    assert attempt.status == terminal_status

    offer_id = order.items[0].offer_id

    expiry_time = order.reservation_expires_at + timedelta(seconds=1)

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=expiry_time,
    )

    assert expired_count == 1

    db_session.expire_all()

    expired_order = db_session.get(
        Order,
        order_id,
    )

    stock_quantity = db_session.scalar(
        select(ProductOffer.stock_quantity).where(ProductOffer.id == offer_id)
    )

    assert expired_order is not None
    assert expired_order.status == "expired"

    # Initial stock 5; checkout reserved 1.
    assert stock_quantity == 5


def test_status_timeout_retry_preserves_pending_attempt(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=(PaymentAttemptStatus.PENDING),
            provider_reference=("status-timeout-1"),
            approval_url=("https://example.invalid/status-timeout-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    provider = TimeoutThenSuccessStatusProvider(db_session)

    with pytest.raises(PaymentProviderUnavailableError):
        refresh_payment_status(
            db_session,
            attempt_id=initiated.attempt_id,
            provider=provider,
        )

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    # Status verification timeout is
    # externally ambiguous. It must not
    # change local payment state.
    assert order.status == "pending"
    assert payment.status == "pending"
    assert attempt.status == PaymentAttemptStatus.PENDING
    assert attempt.provider_reference == "status-timeout-1"

    outcome = refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=provider,
    )

    assert len(provider.calls) == 2

    first_request = provider.calls[0]
    second_request = provider.calls[1]

    assert first_request.attempt_id == second_request.attempt_id == initiated.attempt_id

    assert (
        first_request.provider_reference
        == second_request.provider_reference
        == "status-timeout-1"
    )

    assert outcome.status == PaymentAttemptStatus.SUCCEEDED

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    assert order.status == "paid"
    assert payment.status == "succeeded"
    assert attempt.status == "succeeded"


def test_terminal_status_exact_replay_is_idempotent(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference=("terminal-replay-1"),
            approval_url=("https://example.invalid/terminal-replay-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    success_result = PaymentStatusResult(
        status=PaymentAttemptStatus.SUCCEEDED,
        provider_reference=("terminal-replay-1"),
    )

    status_provider = RecordingStatusProvider(
        db_session,
        success_result,
    )

    first = refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=status_provider,
    )

    assert first.status == PaymentAttemptStatus.SUCCEEDED

    events_before = list_order_events(
        db_session,
        order_id=order_id,
    )

    replayed = reconcile_provider_status(
        db_session,
        attempt_id=initiated.attempt_id,
        result=success_result,
    )

    events_after = list_order_events(
        db_session,
        order_id=order_id,
    )

    assert replayed.id == initiated.attempt_id
    assert replayed.status == "succeeded"

    # Exact terminal replay must not append
    # another paid transition event.
    assert len(events_after) == len(events_before)

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    assert order is not None
    assert payment is not None

    assert order.status == "paid"
    assert payment.status == "succeeded"


@pytest.mark.parametrize(
    "conflicting_result",
    [
        PaymentStatusResult(
            status=PaymentAttemptStatus.FAILED,
            provider_reference=("terminal-conflict-1"),
            failure_code="provider_declined",
        ),
        PaymentStatusResult(
            status=PaymentAttemptStatus.SUCCEEDED,
            provider_reference=("different-provider-reference"),
        ),
    ],
)
def test_terminal_status_conflict_cannot_rewrite_success(
    db_session: Session,
    conflicting_result: PaymentStatusResult,
) -> None:
    (
        order_id,
        user_id,
        payment_id,
    ) = _create_payment(db_session)

    reference = "terminal-conflict-1"

    initiation_provider = RecordingProvider(
        db_session,
        PaymentInitiationResult(
            status=PaymentAttemptStatus.PENDING,
            provider_reference=reference,
            approval_url=("https://example.invalid/terminal-conflict-1"),
        ),
    )

    initiated = initiate_payment(
        db_session,
        payment_id=payment_id,
        user_id=user_id,
        provider=initiation_provider,
        idempotency_key=(f"attempt-{uuid4().hex}"),
    )

    status_provider = RecordingStatusProvider(
        db_session,
        PaymentStatusResult(
            status=PaymentAttemptStatus.SUCCEEDED,
            provider_reference=reference,
        ),
    )

    refresh_payment_status(
        db_session,
        attempt_id=initiated.attempt_id,
        provider=status_provider,
    )

    events_before = list_order_events(
        db_session,
        order_id=order_id,
    )

    with pytest.raises(PaymentProviderResultConflictError):
        reconcile_provider_status(
            db_session,
            attempt_id=initiated.attempt_id,
            result=conflicting_result,
        )

    events_after = list_order_events(
        db_session,
        order_id=order_id,
    )

    db_session.expire_all()

    order = db_session.get(
        Order,
        order_id,
    )

    payment = db_session.get(
        Payment,
        payment_id,
    )

    attempt = db_session.get(
        PaymentAttempt,
        initiated.attempt_id,
    )

    assert order is not None
    assert payment is not None
    assert attempt is not None

    # Conflicting replay must be completely
    # non-destructive.
    assert order.status == "paid"
    assert payment.status == "succeeded"
    assert attempt.status == "succeeded"
    assert attempt.provider_reference == reference

    assert len(events_after) == len(events_before)
