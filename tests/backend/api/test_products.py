from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_offer import ProductOffer


def _create_product(
    db: Session,
    *,
    slug: str,
    active: bool = True,
    category: str = "Testing",
    product_type: str = "component",
) -> Product:
    product = Product(
        slug=slug,
        name=f"Product {slug}",
        description="Product API test",
        product_type=product_type,
        category=category,
        difficulty_level=None,
        image_path=None,
        is_active=active,
    )

    db.add(product)
    db.flush()

    return product


def _add_offer(
    db: Session,
    product: Product,
    *,
    sku: str,
    active: bool = True,
    position: int = 0,
) -> ProductOffer:
    offer = ProductOffer(
        product_id=product.id,
        sku=sku,
        name="Standard",
        pricing_type="fixed",
        fulfillment_type="physical",
        price_cents=1299,
        currency="EUR",
        track_inventory=True,
        stock_quantity=5,
        is_active=active,
        position=position,
    )

    db.add(offer)
    db.flush()

    return offer


def _add_image(
    db: Session,
    product: Product,
    *,
    path: str,
    position: int,
    primary: bool,
) -> ProductImage:
    image = ProductImage(
        product_id=product.id,
        image_path=path,
        alt_text=product.name,
        position=position,
        is_primary=primary,
    )

    db.add(image)
    db.flush()

    return image


def test_product_api_returns_ordered_images(
    client: TestClient,
    db_session: Session,
) -> None:
    product = _create_product(
        db_session,
        slug="api-product-images",
    )

    _add_offer(
        db_session,
        product,
        sku="api-product-images-standard",
    )

    _add_image(
        db_session,
        product,
        path="/assets/test/02.webp",
        position=1,
        primary=False,
    )

    _add_image(
        db_session,
        product,
        path="/assets/test/01.webp",
        position=0,
        primary=True,
    )

    db_session.commit()

    response = client.get("/api/v1/products/api-product-images")

    assert response.status_code == 200

    payload = response.json()

    assert [image["image_path"] for image in payload["images"]] == [
        "/assets/test/01.webp",
        "/assets/test/02.webp",
    ]

    assert payload["images"][0]["is_primary"] is True


def test_product_api_hides_inactive_offers(
    client: TestClient,
    db_session: Session,
) -> None:
    product = _create_product(
        db_session,
        slug="api-hidden-offer",
    )

    _add_offer(
        db_session,
        product,
        sku="api-visible-offer",
        active=True,
        position=0,
    )

    _add_offer(
        db_session,
        product,
        sku="api-hidden-offer",
        active=False,
        position=1,
    )

    db_session.commit()

    response = client.get("/api/v1/products/api-hidden-offer")

    assert response.status_code == 200

    assert [offer["sku"] for offer in response.json()["offers"]] == [
        "api-visible-offer"
    ]


def test_product_api_hides_inactive_product(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_product(
        db_session,
        slug="api-inactive-product",
        active=False,
    )

    db_session.commit()

    response = client.get("/api/v1/products/api-inactive-product")

    assert response.status_code == 404


def test_product_api_filters_category_and_type(
    client: TestClient,
    db_session: Session,
) -> None:
    target = _create_product(
        db_session,
        slug="api-filter-target",
        category="Sensors",
        product_type="component",
    )

    _add_offer(
        db_session,
        target,
        sku="api-filter-target",
    )

    _create_product(
        db_session,
        slug="api-filter-other",
        category="Kits",
        product_type="kit",
    )

    db_session.commit()

    response = client.get(
        "/api/v1/products",
        params={
            "category": "Sensors",
            "product_type": "component",
        },
    )

    assert response.status_code == 200

    slugs = {item["slug"] for item in response.json()}

    assert "api-filter-target" in slugs
    assert "api-filter-other" not in slugs
