from uuid import UUID

from sqlalchemy import (
    Sequence,
    func,
    select,
)
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

ORDER_NUMBER_SEQUENCE = Sequence("order_number_seq")


def next_order_number(
    db: Session,
) -> str:
    sequence_value = db.scalar(select(ORDER_NUMBER_SEQUENCE.next_value()))

    year = db.scalar(
        select(
            func.to_char(
                func.current_date(),
                "YYYY",
            )
        )
    )

    if sequence_value is None or year is None:
        raise RuntimeError("Could not allocate order number.")

    return f"BY-{year}-{sequence_value:08d}"


def create_order(
    db: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_fingerprint: str,
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
    )

    return db.scalar(statement)


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
