from __future__ import annotations

from http.cookies import SimpleCookie

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_cookie import (
    SESSION_COOKIE_NAME,
)
from app.models.user import (
    UserSession,
)


def _credential() -> str:
    return "Strong-" + "api-test-credential-2026!"


def _register(
    client: TestClient,
    email: str,
):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _credential(),
        },
    )


def test_register_sets_httponly_session_cookie(
    client: TestClient,
    db_session: Session,
) -> None:
    response = _register(
        client,
        "customer@example.com",
    )

    assert response.status_code == 201

    body = response.json()

    assert body["email"] == ("customer@example.com")

    assert "session_token" not in body
    assert "password_hash" not in body

    set_cookie = response.headers["set-cookie"]

    assert f"{SESSION_COOKIE_NAME}=" in set_cookie

    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie

    parsed = SimpleCookie()
    parsed.load(set_cookie)

    raw_token = parsed[SESSION_COOKIE_NAME].value

    stored = db_session.scalar(
        select(UserSession).where(UserSession.token_hash != raw_token)
    )

    assert stored is not None
    assert stored.token_hash != raw_token


def test_register_normalizes_email(
    client: TestClient,
) -> None:
    response = _register(
        client,
        "Test.User@Example.COM",
    )

    assert response.status_code == 201

    assert response.json()["email"] == ("test.user@example.com")


def test_duplicate_registration_is_rejected(
    client: TestClient,
) -> None:
    first = _register(
        client,
        "duplicate@example.com",
    )

    assert first.status_code == 201

    second = _register(
        client,
        "DUPLICATE@example.com",
    )

    assert second.status_code == 409

    assert second.json() == {
        "detail": {
            "code": "email_unavailable",
        }
    }


def test_login_uses_generic_credentials_error(
    client: TestClient,
) -> None:
    _register(
        client,
        "existing@example.com",
    )

    wrong = client.post(
        "/api/v1/auth/login",
        json={
            "email": "existing@example.com",
            "password": "wrong-value",
        },
    )

    missing = client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "wrong-value",
        },
    )

    assert wrong.status_code == 401
    assert missing.status_code == 401

    assert wrong.json() == missing.json()

    assert wrong.json() == {
        "detail": {
            "code": "invalid_credentials",
        }
    }


def test_me_returns_authenticated_user(
    client: TestClient,
) -> None:
    registered = _register(
        client,
        "me@example.com",
    )

    assert registered.status_code == 201

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200

    assert response.json()["email"] == ("me@example.com")


def test_me_requires_session(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401

    assert response.json() == {
        "detail": {
            "code": "not_authenticated",
        }
    }


def test_logout_revokes_and_clears_cookie(
    client: TestClient,
) -> None:
    registered = _register(
        client,
        "logout@example.com",
    )

    assert registered.status_code == 201

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204

    me_response = client.get("/api/v1/auth/me")

    assert me_response.status_code == 401


def test_logout_without_session_is_idempotent(
    client: TestClient,
) -> None:
    client.cookies.clear()

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
