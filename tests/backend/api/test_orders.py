from uuid import UUID, uuid4

from factories.catalog import create_product_offer
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderEvent


def _credential() -> str:
    return "Strong-" + "order-api-test-credential-2026!"


def _idempotency_headers(
    key: str | None = None,
) -> dict[str, str]:
    return {"Idempotency-Key": (key or f"test-{uuid4().hex}")}


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
        headers=_idempotency_headers(),
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
        headers=_idempotency_headers(),
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

    order_number = payload["order_number"]

    assert isinstance(
        order_number,
        str,
    )
    assert order_number.startswith("BN-")

    order = db_session.scalar(select(Order).where(Order.id == UUID(payload["id"])))

    assert order is not None

    assert order.user_id == UUID(str(user["id"]))
    assert order.order_number == order_number

    events = list(
        db_session.scalars(
            select(OrderEvent)
            .where(OrderEvent.order_id == order.id)
            .order_by(OrderEvent.id.asc())
        ).all()
    )

    assert [event.event_type for event in events] == [
        "order_created",
        "inventory_reserved",
    ]


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
        headers=_idempotency_headers(),
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
    assert first_history[0]["order_number"] == created.json()["order_number"]

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
        headers=_idempotency_headers(),
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
        headers=_idempotency_headers(),
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
        headers=_idempotency_headers(),
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
        headers=_idempotency_headers(),
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
        headers=_idempotency_headers(),
        json={
            "items": [],
        },
    )

    assert response.status_code == 422


def test_create_order_api_rejects_aggregate_quantity_over_limit(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-order-limit",
        stock_quantity=200,
    )

    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(),
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

    assert response.status_code == 422

    assert response.json()["detail"] == {
        "code": "quantity_limit_exceeded",
        "offer_id": offer.id,
        "requested_quantity": 110,
        "max_quantity": 100,
    }

    db_session.refresh(offer)

    assert offer.stock_quantity == 200


def test_create_order_api_requires_idempotency_key(
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

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "invalid_idempotency_key",
    }


def test_create_order_api_rejects_invalid_idempotency_key(
    client: TestClient,
) -> None:
    _authenticate(client)

    response = client.post(
        "/api/v1/orders",
        headers={
            "Idempotency-Key": "invalid key",
        },
        json={
            "items": [
                {
                    "offer_id": 999999,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "invalid_idempotency_key",
    }


def test_create_order_api_replays_same_key_without_consuming_inventory_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-idempotent-replay",
        price_cents=1200,
        stock_quantity=5,
    )

    db_session.commit()

    key = f"replay-{uuid4().hex}"

    payload = {
        "items": [
            {
                "offer_id": offer.id,
                "quantity": 2,
            }
        ]
    }

    first = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json=payload,
    )

    second = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    assert second.json()["id"] == first.json()["id"]
    assert second.json()["order_number"] == first.json()["order_number"]

    db_session.refresh(offer)

    assert offer.stock_quantity == 3

    orders = list(
        db_session.scalars(
            select(Order).where(Order.user_id == UUID(str(user["id"])))
        ).all()
    )

    assert len(orders) == 1


def test_create_order_api_rejects_same_key_with_different_cart(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-idempotent-conflict",
        price_cents=900,
        stock_quantity=10,
    )

    db_session.commit()

    key = f"conflict-{uuid4().hex}"

    first = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    second = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert first.status_code == 201

    assert second.status_code == 409
    assert second.json()["detail"] == {
        "code": "idempotency_conflict",
    }

    db_session.refresh(offer)

    assert offer.stock_quantity == 9


def test_same_idempotency_key_is_independent_between_users(
    client: TestClient,
    db_session: Session,
) -> None:
    _authenticate(client)

    _, offer = create_product_offer(
        db_session,
        slug="api-idempotent-users",
        price_cents=700,
        stock_quantity=10,
    )

    db_session.commit()

    key = f"shared-{uuid4().hex}"

    first = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    client.cookies.clear()
    _authenticate(client)

    second = client.post(
        "/api/v1/orders",
        headers=_idempotency_headers(key),
        json={
            "items": [
                {
                    "offer_id": offer.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    assert first.json()["id"] != second.json()["id"]

    db_session.refresh(offer)

    assert offer.stock_quantity == 8
