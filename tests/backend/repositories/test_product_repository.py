from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.product_repository import (
    get_active_products_for_update,
)


def _make_product(
    *,
    slug: str,
    name: str,
    stock_quantity: int,
    is_active: bool = True,
) -> Product:
    return Product(
        slug=slug,
        name=name,
        description=None,
        category="Testing",
        image_path=None,
        price_cents=1000,
        currency="EUR",
        stock_quantity=stock_quantity,
        is_active=is_active,
    )


def test_get_active_products_for_update_returns_requested_products(
    db_session: Session,
) -> None:
    first = _make_product(
        slug="repo-test-first",
        name="First",
        stock_quantity=5,
    )
    second = _make_product(
        slug="repo-test-second",
        name="Second",
        stock_quantity=10,
    )

    db_session.add_all(
        [
            first,
            second,
        ]
    )
    db_session.flush()

    result = get_active_products_for_update(
        db_session,
        {
            second.id,
            first.id,
        },
    )

    assert set(result) == {
        first.id,
        second.id,
    }

    assert result[first.id].stock_quantity == 5
    assert result[second.id].stock_quantity == 10


def test_get_active_products_for_update_excludes_inactive_products(
    db_session: Session,
) -> None:
    active = _make_product(
        slug="repo-test-active",
        name="Active",
        stock_quantity=3,
    )
    inactive = _make_product(
        slug="repo-test-inactive",
        name="Inactive",
        stock_quantity=3,
        is_active=False,
    )

    db_session.add_all(
        [
            active,
            inactive,
        ]
    )
    db_session.flush()

    result = get_active_products_for_update(
        db_session,
        {
            active.id,
            inactive.id,
        },
    )

    assert set(result) == {
        active.id,
    }


def test_get_active_products_for_update_accepts_empty_set(
    db_session: Session,
) -> None:
    result = get_active_products_for_update(
        db_session,
        set(),
    )

    assert result == {}
