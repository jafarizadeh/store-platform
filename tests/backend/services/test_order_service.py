import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    MixedCurrencyError,
)
from app.models.order import Order
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import create_pending_order


def _product(
    *,
    slug: str,
    price_cents: int,
    stock_quantity: int,
    currency: str = "EUR",
) -> Product:
    return Product(
        slug=slug,
        name=slug,
        description=None,
        category="Testing",
        image_path=None,
        price_cents=price_cents,
        currency=currency,
        stock_quantity=stock_quantity,
        is_active=True,
    )


def test_create_pending_order_uses_server_prices_and_reduces_stock(
    db_session: Session,
) -> None:
    first = _product(
        slug="order-first",
        price_cents=1200,
        stock_quantity=10,
    )
    second = _product(
        slug="order-second",
        price_cents=500,
        stock_quantity=10,
    )

    db_session.add_all([first, second])
    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=first.id,
                quantity=2,
            ),
            OrderItemCreate(
                product_id=second.id,
                quantity=3,
            ),
        ]
    )

    order = create_pending_order(
        db_session,
        request,
    )

    assert order.status == "pending"
    assert order.currency == "EUR"
    assert order.total_cents == 3900

    assert first.stock_quantity == 8
    assert second.stock_quantity == 7

    assert len(order.items) == 2
    assert order.items[0].unit_price_cents == 1200
    assert order.items[1].unit_price_cents == 500


def test_create_pending_order_aggregates_duplicate_products(
    db_session: Session,
) -> None:
    product = _product(
        slug="order-duplicate",
        price_cents=750,
        stock_quantity=10,
    )

    db_session.add(product)
    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=product.id,
                quantity=2,
            ),
            OrderItemCreate(
                product_id=product.id,
                quantity=3,
            ),
        ]
    )

    order = create_pending_order(
        db_session,
        request,
    )

    assert len(order.items) == 1
    assert order.items[0].quantity == 5
    assert order.total_cents == 3750
    assert product.stock_quantity == 5


def test_create_pending_order_snapshots_product_name_and_price(
    db_session: Session,
) -> None:
    product = _product(
        slug="order-snapshot",
        price_cents=1999,
        stock_quantity=5,
    )
    product.name = "Original product name"

    db_session.add(product)
    db_session.commit()

    order = create_pending_order(
        db_session,
        OrderCreate(
            items=[
                OrderItemCreate(
                    product_id=product.id,
                    quantity=1,
                )
            ]
        ),
    )

    item = order.items[0]

    assert item.product_name == "Original product name"
    assert item.unit_price_cents == 1999


def test_mixed_currency_rolls_back_inventory(
    db_session: Session,
) -> None:
    eur_product = _product(
        slug="order-eur",
        price_cents=1000,
        stock_quantity=5,
        currency="EUR",
    )
    usd_product = _product(
        slug="order-usd",
        price_cents=1000,
        stock_quantity=5,
        currency="USD",
    )

    db_session.add_all(
        [
            eur_product,
            usd_product,
        ]
    )
    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=eur_product.id,
                quantity=1,
            ),
            OrderItemCreate(
                product_id=usd_product.id,
                quantity=1,
            ),
        ]
    )

    with pytest.raises(MixedCurrencyError):
        create_pending_order(
            db_session,
            request,
        )

    db_session.expire_all()

    assert eur_product.stock_quantity == 5
    assert usd_product.stock_quantity == 5

    orders = db_session.scalars(select(Order)).all()

    assert orders == []


def test_insufficient_stock_does_not_create_order(
    db_session: Session,
) -> None:
    product = _product(
        slug="order-no-stock",
        price_cents=1000,
        stock_quantity=1,
    )

    db_session.add(product)
    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=product.id,
                quantity=2,
            )
        ]
    )

    with pytest.raises(InsufficientStockError):
        create_pending_order(
            db_session,
            request,
        )

    orders = db_session.scalars(select(Order)).all()

    assert orders == []
    assert product.stock_quantity == 1
