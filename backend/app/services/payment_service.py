from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.idempotency import (
    is_valid_idempotency_key,
)
from app.domain.order_state import (
    OrderStatus,
)
from app.domain.payment import (
    PaymentStatus,
)
from app.domain.payment_errors import (
    InvalidPaymentIdempotencyKeyError,
    InvalidPaymentProviderError,
    PaymentAttemptIdempotencyConflictError,
    PaymentNotFoundError,
    PaymentNotPendingError,
    PaymentOrderNotPayableError,
    PaymentOrderUnavailableError,
)
from app.models.payment import (
    Payment,
    PaymentAttempt,
)
from app.repositories.order_repository import (
    get_order_for_update,
)
from app.repositories.payment_repository import (
    create_payment,
    create_payment_attempt,
    get_payment_attempt_by_key,
    get_payment_by_id,
    get_payment_by_order_id,
    get_payment_for_update,
)


def _validate_payable_order(
    *,
    order,
    user_id: UUID,
    current_time: datetime,
) -> None:
    if order is None or order.user_id != user_id:
        raise PaymentOrderUnavailableError(
            order.id if order is not None else UUID(int=0)
        )

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
