from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers():
    response = client.get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_request_id_header():
    response = client.get("/health/live")

    request_id = response.headers.get("x-request-id")

    assert request_id is not None
    assert len(request_id) == 32


def test_request_ids_are_unique():
    first = client.get("/health/live")
    second = client.get("/health/live")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_request_id_is_hex():
    response = client.get("/health/live")

    request_id = response.headers["x-request-id"]

    int(request_id, 16)


def test_unknown_route_does_not_leak_internal_details():
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404

    body = response.text.lower()

    assert "traceback" not in body
    assert "/home/" not in body
    assert "sqlalchemy" not in body


def test_large_request_is_rejected():
    response = client.post(
        "/health/live",
        content=b"x" * 1_048_577,
    )

    assert response.status_code == 413


def test_server_does_not_expose_cors_by_default():
    response = client.get(
        "/health/live",
        headers={
            "Origin": "https://evil.example",
        },
    )

    assert "access-control-allow-origin" not in response.headers
