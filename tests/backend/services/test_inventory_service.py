import pytest
from factories.catalog import create_product_offer
from sqlalchemy.orm import Session

from app.domain.order_errors import (
    InsufficientStockError,
    OfferRequiresQuoteError,
    OfferUnavailableError,
)
from app.services.inventory_service import reserve_inventory


def test_reserve_inventory_decrements_tracked_stock(
    db_session: Session,
) -> None:
    _, offer = create_product_offer(
        db_session,
        slug="inventory-tracked",
        stock_quantity=5,
    )

    result = reserve_inventory(
        db_session,
        {offer.id: 2},
    )

    assert result[offer.id] is offer
    assert offer.stock_quantity == 3


def test_reserve_inventory_does_not_decrement_untracked_offer(
    db_session: Session,
) -> None:
    _, offer = create_product_offer(
        db_session,
        slug="inventory-digital",
        fulfillment_type="digital",
        track_inventory=False,
        stock_quantity=0,
    )

    reserve_inventory(
        db_session,
        {offer.id: 50},
    )

    assert offer.stock_quantity == 0


def test_reserve_inventory_rejects_unavailable_offer(
    db_session: Session,
) -> None:
    unavailable_offer_id = 999_999

    with pytest.raises(OfferUnavailableError) as error:
        reserve_inventory(
            db_session,
            {unavailable_offer_id: 1},
        )

    assert error.value.offer_id == unavailable_offer_id


def test_reserve_inventory_rejects_quote_offer(
    db_session: Session,
) -> None:
    _, offer = create_product_offer(
        db_session,
        slug="inventory-quote",
        pricing_type="quote",
        fulfillment_type="service",
        price_cents=None,
        currency=None,
        track_inventory=False,
    )

    with pytest.raises(OfferRequiresQuoteError) as error:
        reserve_inventory(
            db_session,
            {offer.id: 1},
        )

    assert error.value.offer_id == offer.id


def test_insufficient_stock_causes_no_partial_mutation(
    db_session: Session,
) -> None:
    _, first = create_product_offer(
        db_session,
        slug="inventory-first",
        stock_quantity=10,
    )

    _, second = create_product_offer(
        db_session,
        slug="inventory-second",
        stock_quantity=1,
    )

    with pytest.raises(InsufficientStockError) as error:
        reserve_inventory(
            db_session,
            {
                first.id: 3,
                second.id: 2,
            },
        )

    assert error.value.offer_id == second.id
    assert error.value.requested_quantity == 2
    assert error.value.available_quantity == 1

    assert first.stock_quantity == 10
    assert second.stock_quantity == 1
