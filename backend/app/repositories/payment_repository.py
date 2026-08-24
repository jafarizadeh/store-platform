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
    statement = (
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
        .execution_options(
            populate_existing=True,
        )
    )

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


def get_unresolved_payment_attempt(
    db: Session,
    *,
    payment_id: UUID,
) -> PaymentAttempt | None:
    statement = (
        select(PaymentAttempt)
        .where(
            PaymentAttempt.payment_id == payment_id,
            PaymentAttempt.status.in_(
                (
                    PaymentAttemptStatus.CREATED.value,
                    PaymentAttemptStatus.PENDING.value,
                )
            ),
        )
        .order_by(
            PaymentAttempt.created_at,
            PaymentAttempt.id,
        )
        .limit(1)
    )

    return db.scalar(statement)


def get_payment_attempt_with_payment(
    db: Session,
    *,
    attempt_id: UUID,
) -> PaymentAttempt | None:
    statement = (
        select(PaymentAttempt)
        .options(selectinload(PaymentAttempt.payment))
        .where(PaymentAttempt.id == attempt_id)
    )

    return db.scalar(statement)


def get_payment_attempt_by_id(
    db: Session,
    *,
    attempt_id: UUID,
) -> PaymentAttempt | None:
    return db.get(
        PaymentAttempt,
        attempt_id,
    )


def get_payment_attempt_for_update(
    db: Session,
    *,
    attempt_id: UUID,
) -> PaymentAttempt | None:
    statement = (
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(
            populate_existing=True,
        )
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


def get_order_ids_with_unresolved_payment_attempts(
    db: Session,
    *,
    order_ids: list[UUID],
) -> set[UUID]:
    if not order_ids:
        return set()

    statement = (
        select(Payment.order_id)
        .join(
            PaymentAttempt,
            PaymentAttempt.payment_id == Payment.id,
        )
        .where(
            Payment.order_id.in_(order_ids),
            PaymentAttempt.status.in_(
                (
                    PaymentAttemptStatus.CREATED.value,
                    PaymentAttemptStatus.PENDING.value,
                )
            ),
        )
        .distinct()
    )

    return set(db.scalars(statement).all())
