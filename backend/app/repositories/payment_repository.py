from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.domain.payment import (
    PaymentAttemptStatus,
    PaymentStatus,
)
from app.models.payment import (
    Payment,
    PaymentAttempt,
)


def get_payment_by_order_id(
    db: Session,
    *,
    order_id: UUID,
) -> Payment | None:
    statement = (
        select(Payment)
        .options(selectinload(Payment.attempts))
        .where(Payment.order_id == order_id)
    )

    return db.scalar(statement)


def get_payment_by_id(
    db: Session,
    *,
    payment_id: UUID,
) -> Payment | None:
    return db.get(
        Payment,
        payment_id,
    )


def get_payment_for_update(
    db: Session,
    *,
    payment_id: UUID,
) -> Payment | None:
    statement = select(Payment).where(Payment.id == payment_id).with_for_update()

    return db.scalar(statement)


def create_payment(
    db: Session,
    *,
    order_id: UUID,
    amount_cents: int,
    currency: str,
) -> Payment:
    payment = Payment(
        order_id=order_id,
        status=PaymentStatus.PENDING.value,
        amount_cents=amount_cents,
        currency=currency,
    )

    db.add(payment)
    db.flush()

    return payment


def get_payment_attempt_by_key(
    db: Session,
    *,
    payment_id: UUID,
    idempotency_key: str,
) -> PaymentAttempt | None:
    statement = select(PaymentAttempt).where(
        PaymentAttempt.payment_id == payment_id,
        PaymentAttempt.idempotency_key == idempotency_key,
    )

    return db.scalar(statement)


def create_payment_attempt(
    db: Session,
    *,
    payment_id: UUID,
    idempotency_key: str,
    provider: str,
) -> PaymentAttempt:
    attempt = PaymentAttempt(
        payment_id=payment_id,
        idempotency_key=idempotency_key,
        provider=provider,
        status=(PaymentAttemptStatus.CREATED.value),
    )

    db.add(attempt)
    db.flush()

    return attempt
