from __future__ import annotations

from typing import Annotated

from fastapi import (
    Cookie,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.auth_cookie import (
    SESSION_COOKIE_NAME,
)
from app.db.session import get_db
from app.domain.auth_errors import (
    InvalidSessionError,
)
from app.services.auth_service import (
    AuthenticatedSession,
    authenticate_session,
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def require_authenticated_session(
    db: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(
            alias=SESSION_COOKIE_NAME,
        ),
    ] = None,
) -> AuthenticatedSession:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "not_authenticated",
            },
        )

    try:
        return authenticate_session(
            db,
            session_token,
        )

    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "not_authenticated",
            },
        ) from exc
