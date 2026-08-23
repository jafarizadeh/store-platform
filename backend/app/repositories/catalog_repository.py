from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_offer import ProductOffer


def _public_product_options():
    return (
        selectinload(Product.offers.and_(ProductOffer.is_active.is_(True))),
        selectinload(Product.images),
    )


def list_active_products(
    db: Session,
    *,
    category: str | None,
    product_type: str | None,
    limit: int,
    offset: int,
) -> list[Product]:
    statement = (
        select(Product)
        .where(Product.is_active.is_(True))
        .options(*_public_product_options())
        .execution_options(populate_existing=True)
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )

    if category is not None:
        statement = statement.where(Product.category == category)

    if product_type is not None:
        statement = statement.where(Product.product_type == product_type)

    return list(db.scalars(statement).all())


def get_active_product_by_slug(
    db: Session,
    slug: str,
) -> Product | None:
    statement = (
        select(Product)
        .where(
            Product.slug == slug,
            Product.is_active.is_(True),
        )
        .options(*_public_product_options())
        .execution_options(populate_existing=True)
    )

    return db.scalar(statement)
