from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_offer import ProductOffer
from app.repositories.catalog_repository import (
    get_active_product_by_slug,
    list_active_products,
)


def _create_product(
    db: Session,
    *,
    slug: str,
    is_active: bool = True,
) -> Product:
    product = Product(
        slug=slug,
        name=f"Product {slug}",
        description="Catalog repository test",
        product_type="component",
        category="Testing",
        difficulty_level=None,
        image_path=None,
        is_active=is_active,
    )

    db.add(product)
    db.flush()

    return product


def _add_offer(
    db: Session,
    product: Product,
    *,
    sku: str,
    is_active: bool,
    position: int,
) -> None:
    db.add(
        ProductOffer(
            product_id=product.id,
            sku=sku,
            name="Standard",
            pricing_type="fixed",
            fulfillment_type="physical",
            price_cents=1000,
            currency="EUR",
            track_inventory=True,
            stock_quantity=5,
            is_active=is_active,
            position=position,
        )
    )


def _add_image(
    db: Session,
    product: Product,
    *,
    path: str,
    position: int,
    is_primary: bool,
) -> None:
    db.add(
        ProductImage(
            product_id=product.id,
            image_path=path,
            alt_text=product.name,
            position=position,
            is_primary=is_primary,
        )
    )


def test_list_catalog_loads_images_and_active_offers(
    db_session: Session,
) -> None:
    product = _create_product(
        db_session,
        slug="catalog-repository",
    )

    _add_offer(
        db_session,
        product,
        sku="catalog-active",
        is_active=True,
        position=0,
    )

    _add_offer(
        db_session,
        product,
        sku="catalog-inactive",
        is_active=False,
        position=1,
    )

    _add_image(
        db_session,
        product,
        path="/images/02.webp",
        position=1,
        is_primary=False,
    )

    _add_image(
        db_session,
        product,
        path="/images/01.webp",
        position=0,
        is_primary=True,
    )

    db_session.commit()

    products = list_active_products(
        db_session,
        category="Testing",
        product_type="component",
        limit=50,
        offset=0,
    )

    result = next(item for item in products if item.slug == "catalog-repository")

    assert [image.image_path for image in result.images] == [
        "/images/01.webp",
        "/images/02.webp",
    ]

    assert [offer.sku for offer in result.offers] == ["catalog-active"]


def test_get_catalog_hides_inactive_product(
    db_session: Session,
) -> None:
    _create_product(
        db_session,
        slug="catalog-inactive-product",
        is_active=False,
    )

    db_session.commit()

    assert (
        get_active_product_by_slug(
            db_session,
            "catalog-inactive-product",
        )
        is None
    )
