from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


def get_active_products_for_update(
    db: Session,
    product_ids: set[int],
) -> dict[int, Product]:
    if not product_ids:
        return {}

    statement = (
        select(Product)
        .where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
        )
        .order_by(Product.id)
        .with_for_update()
    )

    products = db.scalars(statement).all()

    return {product.id: product for product in products}
