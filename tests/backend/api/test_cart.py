from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_offer import ProductOffer


def _create_offer(
    db: Session,
    *,
    slug: str,
    sku: str,
    price_cents: int = 1299,
    currency: str = "EUR",
    stock_quantity: int = 5,
    track_inventory: bool = True,
    product_active: bool = True,
    offer_active: bool = True,
    pricing_type: str = "fixed",
) -> ProductOffer:
    product = Product(
        slug=slug,
        name=f"Product {slug}",
        description="Cart validation test",
        product_type="component",
        category="Testing",
        difficulty_level=None,
        image_path=None,
        is_active=product_active,
    )

    db.add(product)
    db.flush()

    image = ProductImage(
        product_id=product.id,
        image_path=f"/assets/test/{slug}.webp",
        alt_text=product.name,
        position=0,
        is_primary=True,
    )

    db.add(image)

    offer = ProductOffer(
        product_id=product.id,
        sku=sku,
        name="Standard",
        pricing_type=pricing_type,
        fulfillment_type="physical",
        price_cents=(price_cents if pricing_type == "fixed" else None),
        currency=(currency if pricing_type == "fixed" else None),
        track_inventory=track_inventory,
        stock_quantity=stock_quantity,
        is_active=offer_active,
        position=0,
    )

    db.add(offer)
    db.flush()

    return offer


def test_cart_validation_returns_authoritative_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    offer = _create_offer(
        db_session,
        slug="cart-authoritative",
        sku="CART-AUTH",
        price_cents=1499,
        stock_quantity=7,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["valid"] is True
    assert payload["currency"] == "EUR"
    assert payload["subtotal_cents"] == 2998
    assert payload["mixed_currency"] is False

    item = payload["items"][0]

    assert item["offer_id"] == offer.id
    assert item["requested_quantity"] == 2
    assert item["issue"] is None
    assert item["unit_price_cents"] == 1499
    assert item["max_quantity"] == 7
    assert item["image_path"] == "/assets/test/cart-authoritative.webp"


def test_cart_validation_does_not_reserve_inventory(
    client: TestClient,
    db_session: Session,
) -> None:
    offer = _create_offer(
        db_session,
        slug="cart-no-reserve",
        sku="CART-NO-RESERVE",
        stock_quantity=3,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 200

    db_session.expire_all()

    refreshed = db_session.get(
        ProductOffer,
        offer.id,
    )

    assert refreshed is not None
    assert refreshed.stock_quantity == 3


def test_cart_validation_reports_insufficient_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    offer = _create_offer(
        db_session,
        slug="cart-stock",
        sku="CART-STOCK",
        stock_quantity=1,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["valid"] is False
    assert payload["subtotal_cents"] is None

    item = payload["items"][0]

    assert item["issue"] == "insufficient_stock"
    assert item["available_quantity"] == 1
    assert item["max_quantity"] == 1


def test_cart_validation_reports_unavailable_offer(
    client: TestClient,
    db_session: Session,
) -> None:
    offer = _create_offer(
        db_session,
        slug="cart-unavailable",
        sku="CART-UNAVAILABLE",
        offer_active=False,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["valid"] is False
    assert payload["items"][0]["issue"] == "offer_unavailable"


def test_cart_validation_reports_mixed_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    eur_offer = _create_offer(
        db_session,
        slug="cart-eur",
        sku="CART-EUR",
        currency="EUR",
    )

    usd_offer = _create_offer(
        db_session,
        slug="cart-usd",
        sku="CART-USD",
        currency="USD",
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": eur_offer.id,
                    "quantity": 1,
                },
                {
                    "offer_id": usd_offer.id,
                    "quantity": 1,
                },
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["valid"] is False
    assert payload["mixed_currency"] is True
    assert payload["currency"] is None
    assert payload["subtotal_cents"] is None


def test_cart_validation_enforces_aggregate_quantity_limit(
    client: TestClient,
    db_session: Session,
) -> None:
    offer = _create_offer(
        db_session,
        slug="cart-quantity-limit",
        sku="CART-QUANTITY-LIMIT",
        stock_quantity=200,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/cart/validate",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 60,
                },
                {
                    "offer_id": offer.id,
                    "quantity": 50,
                },
            ]
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["valid"] is False
    assert payload["subtotal_cents"] is None

    assert payload["items"][0]["issue"] == "quantity_limit_exceeded"
    assert payload["items"][0]["requested_quantity"] == 110
    assert payload["items"][0]["max_quantity"] == 100
