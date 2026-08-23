from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(
    db: Session,
    user_id: uuid.UUID,
) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))


def get_user_by_id_for_update(
    db: Session,
    user_id: uuid.UUID,
) -> User | None:
    return db.scalar(select(User).where(User.id == user_id).with_for_update())


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
    )

    db.add(user)
    db.flush()

    return user


def update_password_hash(
    db: Session,
    user: User,
    password_hash: str,
) -> None:
    user.password_hash = password_hash

    db.add(user)
    db.flush()
