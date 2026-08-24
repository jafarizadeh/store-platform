from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_offer import ProductOffer


def get_offers_for_update(
    db: Session,
    offer_ids: set[int],
) -> dict[int, ProductOffer]:
    if not offer_ids:
        return {}

    statement = (
        select(ProductOffer)
        .where(ProductOffer.id.in_(offer_ids))
        .order_by(ProductOffer.id)
        .with_for_update()
    )

    offers = db.scalars(statement).all()

    return {offer.id: offer for offer in offers}


def get_active_offers_for_update(
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
        .options(selectinload(ProductOffer.product))
        .order_by(ProductOffer.id)
        .with_for_update()
    )

    offers = db.scalars(statement).all()

    return {offer.id: offer for offer in offers}
