from uuid import UUID, uuid4

from factories.catalog import create_product_offer
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order


def _credential() -> str:
    return "Strong-" + "order-api-test-credential-2026!"


def _authenticate(
    client: TestClient,
) -> dict[str, object]:
    email = f"order-{uuid4().hex}@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _credential(),
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_order_api_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": 1,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 401

    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
        }
    }


def test_create_order_api_returns_server_calculated_total(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _authenticate(client)

    _, first = create_product_offer(
        db_session,
        slug="api-order-first",
        price_cents=1500,
    )

    _, second = create_product_offer(
        db_session,
        slug="api-order-second",
        price_cents=250,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": first.id,
                    "quantity": 2,
                },
                {
                    "offer_id": second.id,
                    "quantity": 4,
                },
            ]
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["status"] == "pending"
    assert payload["currency"] == "EUR"
    assert payload["total_cents"] == 4000
    assert len(payload["items"]) == 2

    order = db_session.scalar(select(Order).where(Order.id == UUID(payload["id"])))

    assert order is not None

    assert order.user_id == UUID(str(user["id"]))


def test_order_history_returns_only_current_users_orders(
    client: TestClient,
    db_session: Session,
) -> None:
    first_user = _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-owned-order",
        price_cents=1299,
        stock_quantity=10,
    )

    db_session.commit()

    created = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert created.status_code == 201

    history = client.get("/api/v1/orders")

    assert history.status_code == 200

    first_history = history.json()

    assert len(first_history) == 1
    assert first_history[0]["id"] == created.json()["id"]

    client.cookies.clear()

    second_user = _authenticate(client)

    assert second_user["id"] != first_user["id"]

    second_history = client.get("/api/v1/orders")

    assert second_history.status_code == 200
    assert second_history.json() == []


def test_order_history_requires_authentication(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.get("/api/v1/orders")

    assert response.status_code == 401


def test_create_order_api_rejects_unavailable_offer(
    client: TestClient,
) -> None:
    _authenticate(client)

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": 999999,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "offer_unavailable",
        "offer_id": 999999,
    }


def test_create_order_api_rejects_insufficient_stock(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-order-stock",
        stock_quantity=1,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "insufficient_stock",
        "offer_id": offer.id,
        "requested_quantity": 2,
        "available_quantity": 1,
    }


def test_create_order_api_rejects_quote_offer(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-order-quote",
        pricing_type="quote",
        fulfillment_type="service",
        price_cents=None,
        currency=None,
        track_inventory=False,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "quote_required",
        "offer_id": offer.id,
    }


def test_create_order_api_rejects_mixed_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, eur_offer = create_product_offer(
        db_session,
        slug="api-order-eur",
        currency="EUR",
    )

    _, usd_offer = create_product_offer(
        db_session,
        slug="api-order-usd",
        currency="USD",
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
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

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "mixed_currency",
    }


def test_create_order_api_validates_payload(
    client: TestClient,
) -> None:
    _authenticate(client)

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [],
        },
    )

    assert response.status_code == 422
