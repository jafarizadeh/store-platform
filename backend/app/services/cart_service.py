from collections import defaultdict

from sqlalchemy.orm import Session

from app.repositories.cart_repository import (
    get_active_cart_offers,
)
from app.schemas.cart import (
    CartValidationItemResponse,
    CartValidationRequest,
    CartValidationResponse,
)

MAX_ORDER_QUANTITY_PER_OFFER = 100


def validate_cart(
    db: Session,
    request: CartValidationRequest,
) -> CartValidationResponse:
    quantities: dict[int, int] = defaultdict(int)

    for item in request.items:
        quantities[item.offer_id] += item.quantity

    offers = get_active_cart_offers(
        db,
        set(quantities),
    )

    response_items: list[CartValidationItemResponse] = []

    currencies: set[str] = set()
    subtotal_cents = 0
    valid = True

    for offer_id, quantity in sorted(quantities.items()):
        offer = offers.get(offer_id)

        if offer is None:
            valid = False

            response_items.append(
                CartValidationItemResponse(
                    offer_id=offer_id,
                    requested_quantity=quantity,
                    issue="offer_unavailable",
                    product_slug=None,
                    product_name=None,
                    offer_name=None,
                    sku=None,
                    fulfillment_type=None,
                    unit_price_cents=None,
                    currency=None,
                    image_path=None,
                    available_quantity=None,
                    max_quantity=None,
                )
            )

            continue

        product = offer.product

        primary_image = next(
            (image for image in product.images if image.is_primary),
            product.images[0] if product.images else None,
        )

        issue = None

        if quantity > MAX_ORDER_QUANTITY_PER_OFFER:
            issue = "quantity_limit_exceeded"
            valid = False
        elif offer.pricing_type != "fixed":
            issue = "quote_required"
            valid = False

        max_quantity = (
            min(
                offer.stock_quantity,
                MAX_ORDER_QUANTITY_PER_OFFER,
            )
            if offer.track_inventory
            else MAX_ORDER_QUANTITY_PER_OFFER
        )

        available_quantity = offer.stock_quantity if offer.track_inventory else None

        if issue is None and offer.track_inventory and quantity > offer.stock_quantity:
            issue = "insufficient_stock"
            valid = False

        if offer.price_cents is not None and offer.currency is not None:
            currencies.add(offer.currency)

            if issue is None:
                subtotal_cents += offer.price_cents * quantity

        response_items.append(
            CartValidationItemResponse(
                offer_id=offer.id,
                requested_quantity=quantity,
                issue=issue,
                product_slug=product.slug,
                product_name=product.name,
                offer_name=offer.name,
                sku=offer.sku,
                fulfillment_type=(offer.fulfillment_type),
                unit_price_cents=(offer.price_cents),
                currency=offer.currency,
                image_path=(
                    primary_image.image_path
                    if primary_image is not None
                    else product.image_path
                ),
                available_quantity=(available_quantity),
                max_quantity=max_quantity,
            )
        )

    mixed_currency = len(currencies) > 1

    if mixed_currency:
        valid = False

    currency = next(iter(currencies)) if len(currencies) == 1 else None

    return CartValidationResponse(
        valid=valid,
        currency=currency,
        subtotal_cents=(subtotal_cents if valid else None),
        mixed_currency=mixed_currency,
        items=response_items,
    )
