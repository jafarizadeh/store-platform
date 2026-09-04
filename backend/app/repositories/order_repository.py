from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.domain.order import (
    OrderLineSnapshot,
)
from app.models.order import (
    Order,
    OrderItem,
)
from app.models.order_number_sequence import (
    OrderDailySequence,
)


def next_order_number(
    db: Session,
) -> str:
    current_date = db.scalar(select(func.current_date()))

    if current_date is None:
        raise RuntimeError("Could not resolve order date.")

    statement = (
        insert(OrderDailySequence)
        .values(
            order_date=current_date,
            last_value=1,
        )
        .on_conflict_do_update(
            index_elements=[OrderDailySequence.order_date],
            set_={
                "last_value": OrderDailySequence.last_value + 1,
            },
        )
        .returning(OrderDailySequence.last_value)
    )

    sequence_value = db.scalar(statement)

    if sequence_value is None:
        raise RuntimeError("Could not allocate order number.")

    if sequence_value > 9999:
        raise RuntimeError("Daily order number capacity exceeded.")

    date_part = current_date.strftime("%y%m%d")

    return f"BN-{date_part}-{sequence_value:04d}"


def create_order(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_fingerprint: str,
    reservation_expires_at: datetime,
    currency: str,
    total_cents: int,
    lines: list[OrderLineSnapshot],
) -> Order:
    order = Order(
        order_number=(next_order_number(db)),
        user_id=user_id,
        idempotency_key=(idempotency_key),
        request_fingerprint=(request_fingerprint),
        status="pending",
        reservation_expires_at=(reservation_expires_at),
        currency=currency,
        total_cents=total_cents,
    )

    order.items = [
        OrderItem(
            offer_id=line.offer_id,
            product_name=(line.product_name),
            offer_name=line.offer_name,
            sku=line.sku,
            fulfillment_type=(line.fulfillment_type),
            unit_price_cents=(line.unit_price_cents),
            quantity=line.quantity,
        )
        for line in lines
    ]

    db.add(order)
    db.flush()

    return order


def get_order_by_idempotency_key(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
) -> Order | None:
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.user_id == user_id,
            Order.idempotency_key == idempotency_key,
        )
    )

    return db.scalar(statement)


def get_order_for_update(
    db: Session,
    *,
    order_id: UUID,
) -> Order | None:
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
        .with_for_update()
        .execution_options(
            populate_existing=True,
        )
    )

    return db.scalar(statement)


def get_due_pending_orders_for_update(
    db: Session,
    *,
    current_time: datetime,
    limit: int,
) -> list[Order]:
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.status == "pending",
            Order.reservation_expires_at <= current_time,
        )
        .order_by(
            Order.reservation_expires_at,
            Order.id,
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )

    return list(db.scalars(statement).unique().all())


def list_orders_for_user(
    db: Session,
    user_id: UUID,
) -> list[Order]:
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(
            Order.created_at.desc(),
            Order.id.desc(),
        )
    )

    return list(db.scalars(statement).unique().all())
