import re

IDEMPOTENCY_KEY_MIN_LENGTH = 16
IDEMPOTENCY_KEY_MAX_LENGTH = 128

_IDEMPOTENCY_KEY_PATTERN = re.compile(
    rf"^[A-Za-z0-9._~-]"
    rf"{{{IDEMPOTENCY_KEY_MIN_LENGTH},"
    rf"{IDEMPOTENCY_KEY_MAX_LENGTH}}}$"
)


def is_valid_idempotency_key(
    value: str | None,
) -> bool:
    if value is None:
        return False

    return _IDEMPOTENCY_KEY_PATTERN.fullmatch(value) is not None
