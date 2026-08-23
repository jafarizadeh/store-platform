from factories.catalog import create_product_offer
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_create_order_api_returns_server_calculated_total(
    client: TestClient,
    db_session: Session,
) -> None:
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


def test_create_order_api_rejects_unavailable_offer(
    client: TestClient,
) -> None:
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
    response = client.post(
        "/api/v1/orders",
        json={"items": []},
    )

    assert response.status_code == 422
