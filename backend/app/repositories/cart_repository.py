from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_offer import ProductOffer


def get_active_cart_offers(
    db: Session,
    offer_ids: set[int],
) -> dict[int, ProductOffer]:
    if not offer_ids:
        return {}

    statement = (
        select(ProductOffer)
        .join(
            Product,
            Product.id == ProductOffer.product_id,
        )
        .where(
            ProductOffer.id.in_(offer_ids),
            ProductOffer.is_active.is_(True),
            Product.is_active.is_(True),
        )
        .options(selectinload(ProductOffer.product).selectinload(Product.images))
        .order_by(ProductOffer.id)
    )

    offers = db.scalars(statement).unique().all()

    return {offer.id: offer for offer in offers}
