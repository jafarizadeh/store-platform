from collections import defaultdict

from sqlalchemy.orm import Session

from app.domain.order import OrderLineSnapshot
from app.domain.order_errors import MixedCurrencyError
from app.models.order import Order
from app.repositories.order_repository import create_order
from app.schemas.order import OrderCreate
from app.services.inventory_service import reserve_inventory


def _aggregate_quantities(
    request: OrderCreate,
) -> dict[int, int]:
    quantities: dict[int, int] = defaultdict(int)

    for item in request.items:
        quantities[item.product_id] += item.quantity

    return dict(quantities)


def create_pending_order(
    db: Session,
    request: OrderCreate,
) -> Order:
    requested_quantities = _aggregate_quantities(request)

    with db.begin():
        products = reserve_inventory(
            db,
            requested_quantities,
        )

        currencies = {product.currency for product in products.values()}

        if len(currencies) != 1:
            raise MixedCurrencyError

        currency = currencies.pop()

        lines = [
            OrderLineSnapshot(
                product_id=product_id,
                product_name=products[product_id].name,
                unit_price_cents=products[product_id].price_cents,
                quantity=quantity,
            )
            for product_id, quantity in sorted(requested_quantities.items())
        ]

        total_cents = sum(line.unit_price_cents * line.quantity for line in lines)

        order = create_order(
            db,
            currency=currency,
            total_cents=total_cents,
            lines=lines,
        )

    return order
