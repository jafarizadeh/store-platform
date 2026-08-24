from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.idempotency import (
    is_valid_idempotency_key,
)
from app.domain.order_event import (
    OrderActorType,
    OrderEventSource,
    OrderEventType,
)
from app.domain.order_state import (
    OrderStatus,
    is_order_transition_allowed,
)
from app.domain.payment import (
    PaymentStatus,
)
from app.domain.payment_errors import (
    InvalidPaymentIdempotencyKeyError,
    InvalidPaymentProviderError,
    PaymentAttemptAlreadyActiveError,
    PaymentAttemptIdempotencyConflictError,
    PaymentAttemptNotFoundError,
    PaymentNotFoundError,
    PaymentNotPendingError,
    PaymentOrderNotPayableError,
    PaymentOrderUnavailableError,
)
from app.models.payment import (
    Payment,
    PaymentAttempt,
)
from app.repositories.order_event_repository import (
    append_order_event,
)
from app.repositories.order_repository import (
    get_order_for_update,
)
from app.repositories.payment_repository import (
    create_payment,
    create_payment_attempt,
    get_payment_attempt_by_key,
    get_payment_attempt_for_update,
    get_payment_attempt_with_payment,
    get_payment_by_id,
    get_payment_by_order_id,
    get_payment_for_update,
    get_unresolved_payment_attempt,
)


def _validate_payable_order(
    *,
    order,
    user_id: UUID,
    current_time: datetime,
) -> None:
    if order is None:
        raise RuntimeError("Payable-order validation received no order.")

    if order.user_id != user_id:
        raise PaymentOrderUnavailableError(order.id)

    if order.status != OrderStatus.PENDING.value:
        raise PaymentOrderNotPayableError(
            order_id=order.id,
            current_status=order.status,
            reason="order_not_pending",
        )

    if order.reservation_expires_at <= current_time:
        raise PaymentOrderNotPayableError(
            order_id=order.id,
            current_status=order.status,
            reason="reservation_expired",
        )


def prepare_payment(
    db: Session,
    *,
    order_id: UUID,
    user_id: UUID,
    current_time: datetime | None = None,
) -> Payment:
    if current_time is None:
        current_time = datetime.now(UTC)

    try:
        order = get_order_for_update(
            db,
            order_id=order_id,
        )

        if order is None:
            raise PaymentOrderUnavailableError(order_id)

        _validate_payable_order(
            order=order,
            user_id=user_id,
            current_time=current_time,
        )

        existing = get_payment_by_order_id(
            db,
            order_id=order.id,
        )

        if existing is not None:
            db.commit()
            return existing

        payment = create_payment(
            db,
            order_id=order.id,
            amount_cents=order.total_cents,
            currency=order.currency,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return payment


def prepare_payment_attempt(
    db: Session,
    *,
    payment_id: UUID,
    user_id: UUID,
    provider: str,
    idempotency_key: str,
    current_time: datetime | None = None,
) -> PaymentAttempt:
    if current_time is None:
        current_time = datetime.now(UTC)

    normalized_provider = provider.strip().lower()

    if not normalized_provider or len(normalized_provider) > 40:
        raise InvalidPaymentProviderError

    if not is_valid_idempotency_key(idempotency_key):
        raise (InvalidPaymentIdempotencyKeyError)

    try:
        payment_snapshot = get_payment_by_id(
            db,
            payment_id=payment_id,
        )

        if payment_snapshot is None:
            raise PaymentNotFoundError(payment_id)

        # Lock order first everywhere to
        # preserve deterministic lock order.
        order = get_order_for_update(
            db,
            order_id=(payment_snapshot.order_id),
        )

        if order is None:
            raise PaymentOrderUnavailableError(payment_snapshot.order_id)

        _validate_payable_order(
            order=order,
            user_id=user_id,
            current_time=current_time,
        )

        payment = get_payment_for_update(
            db,
            payment_id=payment_id,
        )

        if payment is None:
            raise PaymentNotFoundError(payment_id)

        if payment.status != PaymentStatus.PENDING.value:
            raise PaymentNotPendingError(
                payment_id=payment.id,
                current_status=(payment.status),
            )

        existing = get_payment_attempt_by_key(
            db,
            payment_id=payment.id,
            idempotency_key=(idempotency_key),
        )

        if existing is not None:
            if existing.provider != normalized_provider:
                raise (PaymentAttemptIdempotencyConflictError)

            db.commit()
            return existing

        active_attempt = get_unresolved_payment_attempt(
            db,
            payment_id=payment.id,
        )

        if active_attempt is not None:
            raise PaymentAttemptAlreadyActiveError(
                payment_id=payment.id,
                attempt_id=active_attempt.id,
                current_status=active_attempt.status,
            )

        attempt = create_payment_attempt(
            db,
            payment_id=payment.id,
            idempotency_key=(idempotency_key),
            provider=normalized_provider,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return attempt


def prepare_provider_initiation(
    db: Session,
    *,
    payment_id: UUID,
    user_id: UUID,
    provider: str,
    idempotency_key: str,
    current_time: datetime | None = None,
):
    from app.domain.payment import (
        PaymentAttemptStatus,
    )
    from app.payments.provider import (
        PaymentInitiationRequest,
    )

    attempt = prepare_payment_attempt(
        db,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider,
        idempotency_key=idempotency_key,
        current_time=current_time,
    )

    # prepare_payment_attempt committed.
    # Never access expired ORM attributes after
    # this point without explicitly loading them.
    attempt_id = attempt.id

    snapshot = get_payment_attempt_with_payment(
        db,
        attempt_id=attempt_id,
    )

    if snapshot is None:
        db.rollback()
        raise PaymentNotFoundError(payment_id)

    payment = snapshot.payment

    order = get_order_for_update(
        db,
        order_id=payment.order_id,
    )

    if order is None:
        db.rollback()
        raise PaymentOrderUnavailableError(payment.order_id)

    request = PaymentInitiationRequest(
        payment_id=payment.id,
        attempt_id=snapshot.id,
        order_id=order.id,
        order_number=order.order_number,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
    )

    current_status = PaymentAttemptStatus(snapshot.status)

    existing_result = {
        "status": current_status,
        "provider_reference": (snapshot.provider_reference),
        "approval_url": (snapshot.approval_url),
        "failure_code": (snapshot.failure_code),
    }

    # Critical boundary:
    # no DB transaction may survive the
    # external provider call.
    db.commit()

    return request, existing_result


def reconcile_provider_initiation(
    db: Session,
    *,
    attempt_id: UUID,
    result,
) -> PaymentAttempt:
    from app.domain.payment import (
        PaymentAttemptStatus,
        PaymentStatus,
    )
    from app.domain.payment_errors import (
        InvalidPaymentProviderResultError,
        PaymentProviderResultConflictError,
    )
    from app.repositories.payment_repository import (
        get_payment_attempt_with_payment,
    )

    allowed_results = {
        PaymentAttemptStatus.PENDING,
        PaymentAttemptStatus.SUCCEEDED,
        PaymentAttemptStatus.FAILED,
        PaymentAttemptStatus.CANCELLED,
    }

    if result.status not in allowed_results:
        raise InvalidPaymentProviderResultError

    if (
        result.status
        in {
            PaymentAttemptStatus.PENDING,
            PaymentAttemptStatus.SUCCEEDED,
        }
        and not result.provider_reference
    ):
        raise InvalidPaymentProviderResultError

    snapshot = get_payment_attempt_with_payment(
        db,
        attempt_id=attempt_id,
    )

    if snapshot is None:
        db.rollback()
        raise PaymentAttemptNotFoundError(attempt_id)

    payment_id = snapshot.payment_id
    order_id = snapshot.payment.order_id

    try:
        # Global payment lock order:
        # Order -> Payment -> Attempt.
        order = get_order_for_update(
            db,
            order_id=order_id,
        )

        if order is None:
            raise PaymentOrderUnavailableError(order_id)

        payment = get_payment_for_update(
            db,
            payment_id=payment_id,
        )

        if payment is None:
            raise PaymentNotFoundError(payment_id)

        attempt = get_payment_attempt_for_update(
            db,
            attempt_id=attempt_id,
        )

        if attempt is None:
            raise PaymentAttemptNotFoundError(attempt_id)

        stored_status = PaymentAttemptStatus(attempt.status)

        if stored_status != PaymentAttemptStatus.CREATED:
            same_result = (
                stored_status == result.status
                and attempt.provider_reference == result.provider_reference
                and attempt.approval_url == result.approval_url
                and attempt.failure_code == result.failure_code
            )

            if not same_result:
                raise (PaymentProviderResultConflictError)

            db.commit()
            return attempt

        attempt.status = result.status.value
        attempt.provider_reference = result.provider_reference
        attempt.approval_url = result.approval_url
        attempt.failure_code = result.failure_code

        if result.status == PaymentAttemptStatus.SUCCEEDED:
            if payment.status != PaymentStatus.PENDING.value:
                raise PaymentNotPendingError(
                    payment_id=payment.id,
                    current_status=payment.status,
                )

            current_order_status = OrderStatus(order.status)

            if not is_order_transition_allowed(
                current_order_status,
                OrderStatus.PAID,
            ):
                raise PaymentOrderNotPayableError(
                    order_id=order.id,
                    current_status=order.status,
                    reason=("invalid_order_transition"),
                )

            payment.status = PaymentStatus.SUCCEEDED.value
            order.status = OrderStatus.PAID.value

            append_order_event(
                db,
                order_id=order.id,
                event_type=(OrderEventType.ORDER_STATUS_CHANGED),
                actor_type=(OrderActorType.SYSTEM),
                actor_id=None,
                source=(OrderEventSource.PAYMENT_SERVICE),
                event_data={
                    "from_status": (current_order_status.value),
                    "to_status": (OrderStatus.PAID.value),
                    "payment_id": str(payment.id),
                    "payment_attempt_id": str(attempt.id),
                },
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return attempt


def prepare_provider_status_check(
    db: Session,
    *,
    attempt_id: UUID,
    provider: str,
):
    from app.domain.payment import (
        PaymentAttemptStatus,
    )
    from app.domain.payment_errors import (
        PaymentProviderResultConflictError,
    )
    from app.payments.provider import (
        PaymentStatusRequest,
    )

    normalized_provider = provider.strip().lower()

    if not normalized_provider or len(normalized_provider) > 40:
        raise InvalidPaymentProviderError

    try:
        snapshot = get_payment_attempt_with_payment(
            db,
            attempt_id=attempt_id,
        )

        if snapshot is None:
            raise PaymentAttemptNotFoundError(attempt_id)

        if snapshot.provider != normalized_provider:
            raise InvalidPaymentProviderError

        if snapshot.provider_reference is None:
            # CREATED attempts with ambiguous
            # initiation outcomes must be retried
            # through initiation using their stable
            # attempt_id, not status refresh.
            raise PaymentProviderResultConflictError

        payment = snapshot.payment

        order = get_order_for_update(
            db,
            order_id=payment.order_id,
        )

        if order is None:
            raise PaymentOrderUnavailableError(payment.order_id)

        request = PaymentStatusRequest(
            payment_id=payment.id,
            attempt_id=snapshot.id,
            order_id=order.id,
            order_number=order.order_number,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            provider_reference=(snapshot.provider_reference),
        )

        current_status = PaymentAttemptStatus(snapshot.status)

        if current_status == PaymentAttemptStatus.CREATED:
            raise PaymentProviderResultConflictError

        existing = None

        if current_status in {
            PaymentAttemptStatus.SUCCEEDED,
            PaymentAttemptStatus.FAILED,
            PaymentAttemptStatus.CANCELLED,
        }:
            existing = {
                "status": current_status,
                "provider_reference": (snapshot.provider_reference),
                "failure_code": (snapshot.failure_code),
            }

        elif current_status != PaymentAttemptStatus.PENDING:
            raise PaymentProviderResultConflictError

        # Critical network boundary:
        # no transaction survives the provider
        # status/verification call.
        db.commit()

    except Exception:
        db.rollback()
        raise

    return request, existing


def reconcile_provider_status(
    db: Session,
    *,
    attempt_id: UUID,
    result,
) -> PaymentAttempt:
    from app.domain.payment import (
        PaymentAttemptStatus,
        PaymentStatus,
    )
    from app.domain.payment_errors import (
        InvalidPaymentProviderResultError,
        PaymentProviderResultConflictError,
    )

    allowed_results = {
        PaymentAttemptStatus.PENDING,
        PaymentAttemptStatus.SUCCEEDED,
        PaymentAttemptStatus.FAILED,
        PaymentAttemptStatus.CANCELLED,
    }

    if result.status not in allowed_results:
        raise InvalidPaymentProviderResultError

    if not result.provider_reference:
        raise InvalidPaymentProviderResultError

    snapshot = get_payment_attempt_with_payment(
        db,
        attempt_id=attempt_id,
    )

    if snapshot is None:
        db.rollback()
        raise PaymentAttemptNotFoundError(attempt_id)

    payment_id = snapshot.payment_id
    order_id = snapshot.payment.order_id

    try:
        # Global payment lock order:
        # Order -> Payment -> Attempt.
        order = get_order_for_update(
            db,
            order_id=order_id,
        )

        if order is None:
            raise PaymentOrderUnavailableError(order_id)

        payment = get_payment_for_update(
            db,
            payment_id=payment_id,
        )

        if payment is None:
            raise PaymentNotFoundError(payment_id)

        attempt = get_payment_attempt_for_update(
            db,
            attempt_id=attempt_id,
        )

        if attempt is None:
            raise PaymentAttemptNotFoundError(attempt_id)

        stored_status = PaymentAttemptStatus(attempt.status)

        if (
            attempt.provider_reference is None
            or attempt.provider_reference != result.provider_reference
        ):
            raise PaymentProviderResultConflictError

        # Terminal results are immutable.
        # Replaying the exact same result is
        # idempotent; conflicting data is rejected.
        if stored_status in {
            PaymentAttemptStatus.SUCCEEDED,
            PaymentAttemptStatus.FAILED,
            PaymentAttemptStatus.CANCELLED,
        }:
            same_result = (
                stored_status == result.status
                and attempt.provider_reference == result.provider_reference
                and attempt.failure_code == result.failure_code
            )

            if not same_result:
                raise PaymentProviderResultConflictError

            db.commit()
            return attempt

        if stored_status != PaymentAttemptStatus.PENDING:
            raise PaymentProviderResultConflictError

        if payment.status != PaymentStatus.PENDING.value:
            raise PaymentNotPendingError(
                payment_id=payment.id,
                current_status=payment.status,
            )

        attempt.status = result.status.value
        attempt.failure_code = result.failure_code

        if result.status == PaymentAttemptStatus.SUCCEEDED:
            current_order_status = OrderStatus(order.status)

            # IMPORTANT:
            # Do not re-check reservation_expires_at
            # here. While this attempt was PENDING,
            # expiry was blocked by the durable
            # unresolved-attempt guard.
            if not is_order_transition_allowed(
                current_order_status,
                OrderStatus.PAID,
            ):
                raise PaymentOrderNotPayableError(
                    order_id=order.id,
                    current_status=order.status,
                    reason=("invalid_order_transition"),
                )

            payment.status = PaymentStatus.SUCCEEDED.value

            order.status = OrderStatus.PAID.value

            append_order_event(
                db,
                order_id=order.id,
                event_type=(OrderEventType.ORDER_STATUS_CHANGED),
                actor_type=(OrderActorType.SYSTEM),
                actor_id=None,
                source=(OrderEventSource.PAYMENT_SERVICE),
                event_data={
                    "from_status": (current_order_status.value),
                    "to_status": (OrderStatus.PAID.value),
                    "payment_id": str(payment.id),
                    "payment_attempt_id": str(attempt.id),
                },
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return attempt
