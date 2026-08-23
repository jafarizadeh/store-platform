from datetime import (
    UTC,
    datetime,
    timedelta,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_security import (
    generate_session_token,
    hash_password,
    hash_session_token,
)
from app.models.user import (
    User,
    UserSession,
)


def test_user_and_session_can_be_persisted(
    db_session: Session,
) -> None:
    user = User(
        email="customer@example.com",
        password_hash=hash_password("Strong-password-2026!"),
    )

    db_session.add(user)
    db_session.flush()

    raw_token = generate_session_token()

    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=(datetime.now(UTC) + timedelta(days=30)),
    )

    db_session.add(session)
    db_session.flush()

    stored_user = db_session.scalar(select(User).where(User.id == user.id))

    stored_session = db_session.scalar(
        select(UserSession).where(UserSession.id == session.id)
    )

    assert stored_user is not None
    assert stored_user.email == ("customer@example.com")
    assert stored_user.is_active is True

    assert stored_session is not None
    assert stored_session.user_id == (user.id)
    assert stored_session.token_hash != (raw_token)
    assert stored_session.revoked_at is None


def test_user_session_relationship(
    db_session: Session,
) -> None:
    user = User(
        email="relationship@example.com",
        password_hash=hash_password("Strong-password-2026!"),
    )

    session = UserSession(
        token_hash=hash_session_token(generate_session_token()),
        expires_at=(datetime.now(UTC) + timedelta(hours=12)),
    )

    user.sessions.append(session)

    db_session.add(user)
    db_session.flush()

    assert session.user_id == user.id
    assert session.user is user
    assert session in user.sessions
