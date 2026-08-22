from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    ProductUnavailableError,
)
from app.models.product import Product
from app.repositories.product_repository import (
    get_active_products_for_update,
)


def reserve_inventory(
    db: Session,
    requested_quantities: dict[int, int],
) -> dict[int, Product]:
    if not requested_quantities:
        return {}

    products = get_active_products_for_update(
        db,
        set(requested_quantities),
    )

    for product_id in sorted(requested_quantities):
        product = products.get(product_id)

        if product is None:
            raise ProductUnavailableError(product_id)

        requested_quantity = requested_quantities[product_id]

        if product.stock_quantity < requested_quantity:
            raise InsufficientStockError(
                product_id=product_id,
                requested_quantity=requested_quantity,
                available_quantity=product.stock_quantity,
            )

    # Only mutate stock after every requested product has passed
    # validation. The surrounding order transaction will commit
    # or roll back the reservation atomically.
    for product_id, requested_quantity in requested_quantities.items():
        products[product_id].stock_quantity -= requested_quantity

    return products
