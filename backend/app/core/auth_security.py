from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from argon2.low_level import Type

SESSION_TOKEN_BYTES = 32

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(
    password: str,
) -> str:
    return _password_hasher.hash(
        password,
    )


def verify_password(
    password_hash: str,
    password: str,
) -> bool:
    try:
        return _password_hasher.verify(
            password_hash,
            password,
        )
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False


def password_needs_rehash(
    password_hash: str,
) -> bool:
    try:
        return _password_hasher.check_needs_rehash(
            password_hash,
        )
    except InvalidHashError:
        return True


def generate_session_token() -> str:
    return secrets.token_urlsafe(
        SESSION_TOKEN_BYTES,
    )


def hash_session_token(
    token: str,
) -> str:
    return hashlib.sha256(
        token.encode("utf-8"),
    ).hexdigest()


def normalize_email(
    email: str,
) -> str:
    return email.strip().lower()
