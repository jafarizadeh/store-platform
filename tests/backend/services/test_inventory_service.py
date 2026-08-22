import pytest
from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    ProductUnavailableError,
)
from app.models.product import Product
from app.services.inventory_service import reserve_inventory


def _product(
    *,
    slug: str,
    stock_quantity: int,
    is_active: bool = True,
) -> Product:
    return Product(
        slug=slug,
        name=slug,
        description=None,
        category="Testing",
        image_path=None,
        price_cents=1000,
        currency="EUR",
        stock_quantity=stock_quantity,
        is_active=is_active,
    )


def test_reserve_inventory_decrements_stock(
    db_session: Session,
) -> None:
    product = _product(
        slug="inventory-success",
        stock_quantity=5,
    )

    db_session.add(product)
    db_session.flush()

    products = reserve_inventory(
        db_session,
        {
            product.id: 2,
        },
    )

    assert products[product.id] is product
    assert product.stock_quantity == 3


def test_reserve_inventory_rejects_unavailable_product(
    db_session: Session,
) -> None:
    unavailable_product_id = 999_999

    with pytest.raises(ProductUnavailableError) as error:
        reserve_inventory(
            db_session,
            {
                unavailable_product_id: 1,
            },
        )

    assert error.value.product_id == unavailable_product_id


def test_reserve_inventory_rejects_insufficient_stock_without_partial_mutation(
    db_session: Session,
) -> None:
    first = _product(
        slug="inventory-first",
        stock_quantity=10,
    )
    second = _product(
        slug="inventory-second",
        stock_quantity=1,
    )

    db_session.add_all(
        [
            first,
            second,
        ]
    )
    db_session.flush()

    with pytest.raises(InsufficientStockError) as error:
        reserve_inventory(
            db_session,
            {
                first.id: 3,
                second.id: 2,
            },
        )

    assert error.value.product_id == second.id
    assert error.value.requested_quantity == 2
    assert error.value.available_quantity == 1

    assert first.stock_quantity == 10
    assert second.stock_quantity == 1


def test_reserve_inventory_treats_inactive_product_as_unavailable(
    db_session: Session,
) -> None:
    product = _product(
        slug="inventory-inactive",
        stock_quantity=5,
        is_active=False,
    )

    db_session.add(product)
    db_session.flush()

    with pytest.raises(ProductUnavailableError) as error:
        reserve_inventory(
            db_session,
            {
                product.id: 1,
            },
        )

    assert error.value.product_id == product.id
    assert product.stock_quantity == 5
