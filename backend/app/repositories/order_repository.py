from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.order import OrderLineSnapshot
from app.models.order import Order, OrderItem


def create_order(
    db: Session,
    *,
    user_id: UUID,
    currency: str,
    total_cents: int,
    lines: list[OrderLineSnapshot],
) -> Order:
    order = Order(
        user_id=user_id,
        status="pending",
        currency=currency,
        total_cents=total_cents,
    )

    order.items = [
        OrderItem(
            offer_id=line.offer_id,
            product_name=line.product_name,
            offer_name=line.offer_name,
            sku=line.sku,
            fulfillment_type=line.fulfillment_type,
            unit_price_cents=line.unit_price_cents,
            quantity=line.quantity,
        )
        for line in lines
    ]

    db.add(order)
    db.flush()

    return order


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
