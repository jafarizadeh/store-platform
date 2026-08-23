from app.core.auth_security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    password_needs_rehash,
    verify_password,
)


def test_password_hash_uses_argon2id() -> None:
    plaintext = "Strong-test-password-2026!"

    password_hash = hash_password(plaintext)

    assert password_hash.startswith("$argon2id$")
    assert plaintext not in password_hash
    assert verify_password(
        password_hash,
        plaintext,
    )


def test_wrong_password_is_rejected() -> None:
    password_hash = hash_password("correct-password-2026!")

    assert not verify_password(
        password_hash,
        "wrong-password",
    )


def test_invalid_password_hash_is_rejected_safely() -> None:
    assert not verify_password(
        "not-a-valid-password-hash",
        "password",
    )


def test_current_password_hash_does_not_need_rehash() -> None:
    password_hash = hash_password("Another-strong-password-2026!")

    assert not password_needs_rehash(password_hash)


def test_session_tokens_are_random_and_not_stored_directly() -> None:
    token_a = generate_session_token()
    token_b = generate_session_token()

    assert token_a != token_b

    token_hash = hash_session_token(token_a)

    assert token_hash != token_a
    assert len(token_hash) == 64


def test_session_hash_is_deterministic() -> None:
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)


def test_email_normalization() -> None:
    assert normalize_email("  Test.User@Example.COM ") == "test.user@example.com"
