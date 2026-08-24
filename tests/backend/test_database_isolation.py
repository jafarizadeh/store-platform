from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.models.product import Product


def test_backend_tests_use_isolated_database(
    db_session: Session,
) -> None:
    database_name = db_session.scalar(text("SELECT current_database()"))

    assert database_name is not None
    assert database_name.endswith("_test")


def test_session_commit_cannot_escape_test_transaction(
    db_session: Session,
    test_engine: Engine,
) -> None:
    slug = "pytest-transaction-isolation"

    product = Product(
        slug=slug,
        name="Pytest isolation product",
        description=None,
        product_type="component",
        category="Testing",
        difficulty_level=None,
        image_path=None,
        is_active=True,
    )

    db_session.add(product)
    db_session.commit()

    product_in_test_transaction = db_session.scalar(
        select(Product).where(Product.slug == slug)
    )

    assert product_in_test_transaction is not None

    with test_engine.connect() as external_connection:
        externally_visible_count = external_connection.scalar(
            select(func.count()).select_from(Product).where(Product.slug == slug)
        )

    assert externally_visible_count == 0
