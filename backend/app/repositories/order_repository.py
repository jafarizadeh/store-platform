from sqlalchemy.orm import Session

from app.domain.order import OrderLineSnapshot
from app.models.order import Order, OrderItem


def create_order(
    db: Session,
    *,
    currency: str,
    total_cents: int,
    lines: list[OrderLineSnapshot],
) -> Order:
    order = Order(
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
