from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_session_token,
)
from app.domain.auth_errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.models.user import UserSession
from app.services.auth_service import (
    authenticate_session,
    login_user,
    logout_session,
    register_user,
)


def _credential() -> str:
    return "Strong-" + "test-credential-2026!"


def _alternate_credential() -> str:
    return "Another-" + "test-credential-2026!"


def test_register_creates_user_and_session(
    db_session: Session,
) -> None:
    issued = register_user(
        db_session,
        email="  Customer@Example.COM ",
        plaintext_password=_credential(),
    )

    assert issued.user.email == ("customer@example.com")

    assert issued.raw_token

    assert issued.session.token_hash == hash_session_token(issued.raw_token)

    assert issued.session.token_hash != issued.raw_token


def test_duplicate_registration_is_rejected(
    db_session: Session,
) -> None:
    register_user(
        db_session,
        email="duplicate@example.com",
        plaintext_password=_credential(),
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        register_user(
            db_session,
            email="DUPLICATE@example.com",
            plaintext_password=_alternate_credential(),
        )


def test_login_returns_new_session(
    db_session: Session,
) -> None:
    registered = register_user(
        db_session,
        email="login@example.com",
        plaintext_password=_credential(),
    )

    logged_in = login_user(
        db_session,
        email="LOGIN@example.com",
        plaintext_password=_credential(),
    )

    assert logged_in.user.id == registered.user.id

    assert logged_in.raw_token != registered.raw_token


def test_login_uses_generic_invalid_credentials(
    db_session: Session,
) -> None:
    register_user(
        db_session,
        email="existing@example.com",
        plaintext_password=_credential(),
    )

    for email, plaintext in (
        (
            "existing@example.com",
            "wrong-password",
        ),
        (
            "missing@example.com",
            "wrong-password",
        ),
    ):
        with pytest.raises(InvalidCredentialsError):
            login_user(
                db_session,
                email=email,
                plaintext_password=(plaintext),
            )


def test_valid_session_authenticates_user(
    db_session: Session,
) -> None:
    issued = register_user(
        db_session,
        email="session@example.com",
        plaintext_password=_credential(),
    )

    authenticated = authenticate_session(
        db_session,
        issued.raw_token,
    )

    assert authenticated.user.id == issued.user.id


def test_unknown_session_is_rejected(
    db_session: Session,
) -> None:
    with pytest.raises(InvalidSessionError):
        authenticate_session(
            db_session,
            "unknown-session-token",
        )


def test_expired_session_is_rejected(
    db_session: Session,
) -> None:
    issued = register_user(
        db_session,
        email="expired@example.com",
        plaintext_password=_credential(),
    )

    issued.session.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    db_session.flush()

    with pytest.raises(InvalidSessionError):
        authenticate_session(
            db_session,
            issued.raw_token,
        )


def test_logout_revokes_session(
    db_session: Session,
) -> None:
    issued = register_user(
        db_session,
        email="logout@example.com",
        plaintext_password=_credential(),
    )

    logout_session(
        db_session,
        issued.raw_token,
    )

    stored = db_session.scalar(
        select(UserSession).where(UserSession.id == issued.session.id)
    )

    assert stored is not None
    assert stored.revoked_at is not None

    with pytest.raises(InvalidSessionError):
        authenticate_session(
            db_session,
            issued.raw_token,
        )


def test_logout_unknown_token_is_idempotent(
    db_session: Session,
) -> None:
    logout_session(
        db_session,
        "already-gone-token",
    )


def test_register_handles_existing_autobegin_transaction(
    db_session: Session,
) -> None:
    db_session.scalars(select(UserSession.id)).all()

    assert db_session.in_transaction()

    issued = register_user(
        db_session,
        email="autobegin@example.com",
        plaintext_password=_credential(),
    )

    assert issued.raw_token
