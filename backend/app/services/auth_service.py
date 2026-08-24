from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    password_needs_rehash,
    verify_login_password,
)
from app.domain.auth_errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.models.user import User, UserSession
from app.repositories.session_repository import (
    create_session,
    get_session_by_token_hash,
    is_session_active,
    revoke_session,
)
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    update_password_hash,
)

SESSION_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    session: UserSession


@dataclass(frozen=True)
class IssuedSession:
    user: User
    session: UserSession
    raw_token: str


def _issue_session(
    db: Session,
    user: User,
) -> IssuedSession:
    raw_token = generate_session_token()

    session = create_session(
        db,
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=(datetime.now(UTC) + SESSION_LIFETIME),
    )

    return IssuedSession(
        user=user,
        session=session,
        raw_token=raw_token,
    )


def register_user(
    db: Session,
    *,
    email: str,
    plaintext_password: str,
) -> IssuedSession:
    normalized_email = normalize_email(email)

    try:
        if (
            get_user_by_email(
                db,
                normalized_email,
            )
            is not None
        ):
            raise EmailAlreadyRegisteredError

        try:
            user = create_user(
                db,
                email=normalized_email,
                password_hash=hash_password(plaintext_password),
            )
        except IntegrityError as exc:
            raise (EmailAlreadyRegisteredError) from exc

        issued = _issue_session(
            db,
            user,
        )

        db.commit()

        return issued

    except Exception:
        db.rollback()
        raise


def login_user(
    db: Session,
    *,
    email: str,
    plaintext_password: str,
) -> IssuedSession:
    normalized_email = normalize_email(email)

    try:
        user = get_user_by_email(
            db,
            normalized_email,
        )

        password_valid = verify_login_password(
            (user.password_hash if user is not None else None),
            plaintext_password,
        )

        if user is None or not user.is_active or not password_valid:
            raise InvalidCredentialsError

        if password_needs_rehash(user.password_hash):
            update_password_hash(
                db,
                user,
                hash_password(plaintext_password),
            )

        issued = _issue_session(
            db,
            user,
        )

        db.commit()

        return issued

    except Exception:
        db.rollback()
        raise


def authenticate_session(
    db: Session,
    raw_token: str,
) -> AuthenticatedSession:
    session = get_session_by_token_hash(
        db,
        hash_session_token(raw_token),
    )

    if session is None or not is_session_active(session) or not session.user.is_active:
        raise InvalidSessionError

    return AuthenticatedSession(
        user=session.user,
        session=session,
    )


def logout_session(
    db: Session,
    raw_token: str,
) -> None:
    token_hash = hash_session_token(raw_token)

    try:
        session = get_session_by_token_hash(
            db,
            token_hash,
        )

        if session is not None:
            revoke_session(
                db,
                session,
            )

        db.commit()

    except Exception:
        db.rollback()
        raise
