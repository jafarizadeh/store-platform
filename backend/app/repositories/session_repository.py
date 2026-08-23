from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import UserSession


def create_session(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> UserSession:
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(session)
    db.flush()

    return session


def get_session_by_token_hash(
    db: Session,
    token_hash: str,
) -> UserSession | None:
    return db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))


def revoke_session(
    db: Session,
    session: UserSession,
) -> None:
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)

        db.add(session)
        db.flush()


def is_session_active(
    session: UserSession,
    *,
    now: datetime | None = None,
) -> bool:
    current_time = now if now is not None else datetime.now(UTC)

    return session.revoked_at is None and session.expires_at > current_time
