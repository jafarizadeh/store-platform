from __future__ import annotations

from datetime import timedelta

from fastapi import Response

from app.core.config import settings

SESSION_COOKIE_NAME = "bynet_session"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_SAMESITE = "lax"

SESSION_COOKIE_MAX_AGE = int(timedelta(days=30).total_seconds())


def _cookie_secure() -> bool:
    return settings.app_env.strip().lower() in {"production", "prod"}


def set_session_cookie(
    response: Response,
    raw_token: str,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_COOKIE_MAX_AGE,
        path=SESSION_COOKIE_PATH,
        secure=_cookie_secure(),
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def clear_session_cookie(
    response: Response,
) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path=SESSION_COOKIE_PATH,
        secure=_cookie_secure(),
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )
