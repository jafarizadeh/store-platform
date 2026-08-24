from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import UUID, uuid4

import pytest
from factories.catalog import (
    create_product_offer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.domain.order_state import (
    OrderStatus,
)
from app.domain.payment_errors import (
    PaymentAttemptIdempotencyConflictError,
    PaymentOrderNotPayableError,
    PaymentOrderUnavailableError,
)
from app.models.payment import (
    Payment,
    PaymentAttempt,
)
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
    transition_order_status,
)
from app.services.payment_service import (
    prepare_payment,
    prepare_payment_attempt,
)

TEST_CREDENTIAL_HASH = hash_password("payment-foundation-test-credential")


def _user(
    db: Session,
    *,
    suffix: str,
) -> User:
    user = User(
        email=(f"payment-{suffix}-{uuid4().hex}@example.com"),
        password_hash=(TEST_CREDENTIAL_HASH),
        is_active=True,
    )

    db.add(user)
    db.flush()

    return user


def _pending_order(
    db: Session,
) -> tuple[UUID, UUID, int, str]:
    suffix = uuid4().hex

    user = _user(
        db,
        suffix="owner",
    )

    _, offer = create_product_offer(
        db,
        slug=f"payment-{suffix}",
        price_cents=2350,
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
                    quantity=2,
                )
            ]
        ),
        user_id=user.id,
        idempotency_key=(f"order-{uuid4().hex}"),
    )

    return (
        order.id,
        user.id,
        order.total_cents,
        order.currency,
    )


def test_prepare_payment_snapshots_order_amount(
    db_session: Session,
) -> None:
    (
        order_id,
        user_id,
        total_cents,
        currency,
    ) = _pending_order(db_session)

    payment = prepare_payment(
        db_session,
        order_id=order_id,
        user_id=user_id,
    )

    assert payment.order_id == order_id
    assert payment.status == "pending"
    assert payment.amount_cents == total_cents
    assert payment.currency == currency


def test_prepare_payment_is_idempotent_per_order(
    db_session: Session,
) -> None:
    order_id, user_id, _, _ = _pending_order(db_session)

    first = prepare_payment(
        db_session,
        order_id=order_id,
        user_id=user_id,
    )

    second = prepare_payment(
        db_session,
        order_id=order_id,
        user_id=user_id,
    )

    assert first.id == second.id

    payment_ids = list(
        db_session.scalars(select(Payment.id).where(Payment.order_id == order_id)).all()
    )

    assert payment_ids == [first.id]


def test_payment_rejects_expired_reservation(
    db_session: Session,
) -> None:
    order_id, user_id, _, _ = _pending_order(db_session)

    from app.models.order import Order

    order = db_session.get(
        Order,
        order_id,
    )

    assert order is not None

    now = datetime.now(UTC)

    order.reservation_expires_at = now - timedelta(seconds=1)

    db_session.commit()

    with pytest.raises(PaymentOrderNotPayableError) as error:
        prepare_payment(
            db_session,
            order_id=order_id,
            user_id=user_id,
            current_time=now,
        )

    assert error.value.reason == "reservation_expired"


def test_payment_rejects_another_user(
    db_session: Session,
) -> None:
    order_id, _, _, _ = _pending_order(db_session)

    other_user = _user(
        db_session,
        suffix="other",
    )

    db_session.commit()

    with pytest.raises(PaymentOrderUnavailableError):
        prepare_payment(
            db_session,
            order_id=order_id,
            user_id=other_user.id,
        )


def test_payment_rejects_non_pending_order(
    db_session: Session,
) -> None:
    order_id, user_id, _, _ = _pending_order(db_session)

    transition_order_status(
        db_session,
        order_id=order_id,
        target_status=(OrderStatus.PAID),
    )

    with pytest.raises(PaymentOrderNotPayableError) as error:
        prepare_payment(
            db_session,
            order_id=order_id,
            user_id=user_id,
        )

    assert error.value.reason == "order_not_pending"


def test_payment_attempt_is_idempotent(
    db_session: Session,
) -> None:
    order_id, user_id, _, _ = _pending_order(db_session)

    payment = prepare_payment(
        db_session,
        order_id=order_id,
        user_id=user_id,
    )

    key = f"attempt-{uuid4().hex}"

    first = prepare_payment_attempt(
        db_session,
        payment_id=payment.id,
        user_id=user_id,
        provider="PayPal",
        idempotency_key=key,
    )

    second = prepare_payment_attempt(
        db_session,
        payment_id=payment.id,
        user_id=user_id,
        provider="paypal",
        idempotency_key=key,
    )

    assert first.id == second.id
    assert first.provider == "paypal"
    assert first.status == "created"

    attempts = list(
        db_session.scalars(
            select(PaymentAttempt).where(PaymentAttempt.payment_id == payment.id)
        ).all()
    )

    assert len(attempts) == 1


def test_attempt_key_cannot_switch_provider(
    db_session: Session,
) -> None:
    order_id, user_id, _, _ = _pending_order(db_session)

    payment = prepare_payment(
        db_session,
        order_id=order_id,
        user_id=user_id,
    )

    key = f"attempt-{uuid4().hex}"

    prepare_payment_attempt(
        db_session,
        payment_id=payment.id,
        user_id=user_id,
        provider="paypal",
        idempotency_key=key,
    )

    with pytest.raises(PaymentAttemptIdempotencyConflictError):
        prepare_payment_attempt(
            db_session,
            payment_id=payment.id,
            user_id=user_id,
            provider="bank",
            idempotency_key=key,
        )
