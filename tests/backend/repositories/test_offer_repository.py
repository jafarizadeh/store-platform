from factories.catalog import create_product_offer
from sqlalchemy.orm import Session

from app.repositories.offer_repository import (
    get_active_offers_for_update,
)


def test_get_active_offers_for_update_returns_requested_offer(
    db_session: Session,
) -> None:
    product, offer = create_product_offer(
        db_session,
        slug="repo-offer-active",
        stock_quantity=5,
    )

    result = get_active_offers_for_update(
        db_session,
        {offer.id},
    )

    assert set(result) == {offer.id}
    assert result[offer.id].product.id == product.id
    assert result[offer.id].stock_quantity == 5


def test_get_active_offers_for_update_excludes_inactive_catalog_entries(
    db_session: Session,
) -> None:
    _, inactive_offer = create_product_offer(
        db_session,
        slug="repo-offer-inactive",
        offer_active=False,
    )

    _, inactive_product_offer = create_product_offer(
        db_session,
        slug="repo-product-inactive",
        product_active=False,
    )

    result = get_active_offers_for_update(
        db_session,
        {
            inactive_offer.id,
            inactive_product_offer.id,
        },
    )

    assert result == {}


def test_get_active_offers_for_update_accepts_empty_set(
    db_session: Session,
) -> None:
    assert (
        get_active_offers_for_update(
            db_session,
            set(),
        )
        == {}
    )
