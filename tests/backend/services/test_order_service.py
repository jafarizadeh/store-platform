import pytest
from factories.catalog import create_product_offer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    MixedCurrencyError,
)
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import create_pending_order


def test_create_pending_order_uses_server_offer_prices(
    db_session: Session,
) -> None:
    _, first = create_product_offer(
        db_session,
        slug="order-first",
        price_cents=1200,
        stock_quantity=10,
    )

    _, second = create_product_offer(
        db_session,
        slug="order-second",
        price_cents=500,
        stock_quantity=10,
    )

    db_session.commit()

    order = create_pending_order(
        db_session,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=first.id,
                    quantity=2,
                ),
                OrderItemCreate(
                    offer_id=second.id,
                    quantity=3,
                ),
            ]
        ),
    )

    assert order.status == "pending"
    assert order.currency == "EUR"
    assert order.total_cents == 3900

    assert first.stock_quantity == 8
    assert second.stock_quantity == 7


def test_create_pending_order_aggregates_duplicate_offers(
    db_session: Session,
) -> None:
    _, offer = create_product_offer(
        db_session,
        slug="order-duplicate",
        price_cents=750,
        stock_quantity=10,
    )

    db_session.commit()

    order = create_pending_order(
        db_session,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=2,
                ),
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=3,
                ),
            ]
        ),
    )

    assert len(order.items) == 1
    assert order.items[0].quantity == 5
    assert order.total_cents == 3750
    assert offer.stock_quantity == 5


def test_create_pending_order_snapshots_catalog_data(
    db_session: Session,
) -> None:
    product, offer = create_product_offer(
        db_session,
        slug="order-snapshot",
        product_name="Original Product",
        offer_name="Complete Kit",
        sku="snapshot-kit",
        fulfillment_type="physical",
        price_cents=1999,
    )

    db_session.commit()

    order = create_pending_order(
        db_session,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=1,
                )
            ]
        ),
    )

    item = order.items[0]

    assert item.product_name == product.name
    assert item.offer_name == "Complete Kit"
    assert item.sku == "snapshot-kit"
    assert item.fulfillment_type == "physical"
    assert item.unit_price_cents == 1999


def test_mixed_currency_rolls_back_inventory(
    db_session: Session,
) -> None:
    _, eur_offer = create_product_offer(
        db_session,
        slug="order-eur",
        currency="EUR",
        stock_quantity=5,
    )

    _, usd_offer = create_product_offer(
        db_session,
        slug="order-usd",
        currency="USD",
        stock_quantity=5,
    )

    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                offer_id=eur_offer.id,
                quantity=1,
            ),
            OrderItemCreate(
                offer_id=usd_offer.id,
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

    assert eur_offer.stock_quantity == 5
    assert usd_offer.stock_quantity == 5

    matching_order_ids = set(
        db_session.scalars(
            select(Order.id)
            .join(Order.items)
            .where(
                OrderItem.offer_id.in_(
                    {
                        eur_offer.id,
                        usd_offer.id,
                    }
                )
            )
        ).all()
    )

    assert matching_order_ids == set()


def test_insufficient_stock_does_not_create_order(
    db_session: Session,
) -> None:
    _, offer = create_product_offer(
        db_session,
        slug="order-no-stock",
        stock_quantity=1,
    )

    db_session.commit()

    with pytest.raises(InsufficientStockError):
        create_pending_order(
            db_session,
            OrderCreate(
                items=[
                    OrderItemCreate(
                        offer_id=offer.id,
                        quantity=2,
                    )
                ]
            ),
        )

    matching_order_ids = set(
        db_session.scalars(
            select(Order.id).join(Order.items).where(OrderItem.offer_id == offer.id)
        ).all()
    )

    assert matching_order_ids == set()
