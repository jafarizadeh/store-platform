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
        quantities[item.offer_id] += item.quantity

    return dict(quantities)


def create_pending_order(
    db: Session,
    request: OrderCreate,
) -> Order:
    requested_quantities = _aggregate_quantities(request)

    with db.begin():
        offers = reserve_inventory(
            db,
            requested_quantities,
        )

        currencies = {offer.currency for offer in offers.values()}

        if len(currencies) != 1:
            raise MixedCurrencyError

        currency = currencies.pop()

        if currency is None:
            raise RuntimeError("Validated fixed-price offer has no currency.")

        lines: list[OrderLineSnapshot] = []

        for offer_id, quantity in sorted(requested_quantities.items()):
            offer = offers[offer_id]

            if offer.price_cents is None:
                raise RuntimeError("Validated fixed-price offer has no price.")

            lines.append(
                OrderLineSnapshot(
                    offer_id=offer.id,
                    product_name=offer.product.name,
                    offer_name=offer.name,
                    sku=offer.sku,
                    fulfillment_type=(offer.fulfillment_type),
                    unit_price_cents=(offer.price_cents),
                    quantity=quantity,
                )
            )

        total_cents = sum(line.unit_price_cents * line.quantity for line in lines)

        order = create_order(
            db,
            currency=currency,
            total_cents=total_cents,
            lines=lines,
        )

    return order
