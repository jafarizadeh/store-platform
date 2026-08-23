from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    require_authenticated_session,
)
from app.core.auth_cookie import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from app.db.session import get_db
from app.domain.auth_errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import (
    AuthenticatedSession,
    login_user,
    logout_session,
    register_user,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

Authenticated = Annotated[
    AuthenticatedSession,
    Depends(require_authenticated_session),
]

AuthDatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    response: Response,
    db: AuthDatabaseSession,
):
    try:
        issued = register_user(
            db,
            email=str(request.email),
            plaintext_password=request.password,
        )

    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "email_unavailable",
            },
        ) from exc

    set_session_cookie(
        response,
        issued.raw_token,
    )

    return issued.user


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    request: LoginRequest,
    response: Response,
    db: AuthDatabaseSession,
):
    try:
        issued = login_user(
            db,
            email=str(request.email),
            plaintext_password=request.password,
        )

    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
            },
        ) from exc

    set_session_cookie(
        response,
        issued.raw_token,
    )

    return issued.user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    db: AuthDatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(
            alias=SESSION_COOKIE_NAME,
        ),
    ] = None,
) -> None:
    if session_token:
        logout_session(
            db,
            session_token,
        )

    clear_session_cookie(response)


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    authenticated: Authenticated,
):
    return authenticated.user
