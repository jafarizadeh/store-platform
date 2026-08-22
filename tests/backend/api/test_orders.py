from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product


def _product(
    *,
    slug: str,
    price_cents: int,
    stock_quantity: int,
    currency: str = "EUR",
    is_active: bool = True,
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
        is_active=is_active,
    )


def test_create_order_api_returns_server_calculated_total(
    client: TestClient,
    db_session: Session,
) -> None:
    first = _product(
        slug="api-order-first",
        price_cents=1500,
        stock_quantity=10,
    )
    second = _product(
        slug="api-order-second",
        price_cents=250,
        stock_quantity=10,
    )

    db_session.add_all([first, second])
    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": first.id,
                    "quantity": 2,
                },
                {
                    "product_id": second.id,
                    "quantity": 4,
                },
            ],
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["status"] == "pending"
    assert payload["currency"] == "EUR"
    assert payload["total_cents"] == 4000
    assert len(payload["items"]) == 2


def test_create_order_api_rejects_unavailable_product(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": 999999,
                    "quantity": 1,
                }
            ],
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "product_unavailable",
        "product_id": 999999,
    }


def test_create_order_api_rejects_insufficient_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    product = _product(
        slug="api-order-stock",
        price_cents=1000,
        stock_quantity=1,
    )

    db_session.add(product)
    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                }
            ],
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "insufficient_stock",
        "product_id": product.id,
        "requested_quantity": 2,
        "available_quantity": 1,
    }


def test_create_order_api_rejects_mixed_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    eur_product = _product(
        slug="api-order-eur",
        price_cents=1000,
        stock_quantity=5,
        currency="EUR",
    )
    usd_product = _product(
        slug="api-order-usd",
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

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": eur_product.id,
                    "quantity": 1,
                },
                {
                    "product_id": usd_product.id,
                    "quantity": 1,
                },
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "mixed_currency",
    }


def test_create_order_api_validates_payload(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [],
        },
    )

    assert response.status_code == 422
