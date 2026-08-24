from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    OfferRequiresQuoteError,
    OfferUnavailableError,
)
from app.models.product_offer import ProductOffer
from app.repositories.offer_repository import (
    get_active_offers_for_update,
    get_offers_for_update,
)


def reserve_inventory(
    db: Session,
    requested_quantities: dict[int, int],
) -> dict[int, ProductOffer]:
    if not requested_quantities:
        return {}

    offers = get_active_offers_for_update(
        db,
        set(requested_quantities),
    )

    # Validate every line before mutating any inventory.
    for offer_id in sorted(requested_quantities):
        offer = offers.get(offer_id)

        if offer is None:
            raise OfferUnavailableError(offer_id)

        if (
            offer.pricing_type != "fixed"
            or offer.price_cents is None
            or offer.currency is None
        ):
            raise OfferRequiresQuoteError(offer_id)

        requested_quantity = requested_quantities[offer_id]

        if offer.track_inventory and offer.stock_quantity < requested_quantity:
            raise InsufficientStockError(
                offer_id=offer_id,
                requested_quantity=requested_quantity,
                available_quantity=offer.stock_quantity,
            )

    # Only inventory-tracked offers consume stock.
    for offer_id, requested_quantity in requested_quantities.items():
        offer = offers[offer_id]

        if offer.track_inventory:
            offer.stock_quantity -= requested_quantity

    return offers


def release_inventory(
    db: Session,
    released_quantities: dict[int, int],
) -> None:
    if not released_quantities:
        return

    offers = get_offers_for_update(
        db,
        set(released_quantities),
    )

    for offer_id in sorted(released_quantities):
        offer = offers.get(offer_id)

        if offer is None:
            raise RuntimeError(f"Reserved offer no longer exists: {offer_id}.")

        if offer.track_inventory:
            offer.stock_quantity += released_quantities[offer_id]
