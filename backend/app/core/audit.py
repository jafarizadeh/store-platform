from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SECURITY_LOG_PATH = Path(
    os.environ.get(
        "BYNET_SECURITY_LOG_PATH",
        PROJECT_ROOT / "logs/security/security.log",
    )
)


def _bounded(
    value: Any,
    limit: int,
) -> str | None:
    if value is None:
        return None

    return str(value)[:limit]


class SecurityJsonFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event_name", "security_event"),
        }

        fields = (
            "outcome",
            "request_id",
            "actor_type",
            "actor_id",
            "target_type",
            "target_id",
            "source_ip",
            "reason_code",
        )

        for field in fields:
            value = getattr(record, field, None)

            if value is not None:
                payload[field] = value

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )


def _build_security_logger() -> logging.Logger:
    logger = logging.getLogger("bynet.security")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    SECURITY_LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    handler = logging.FileHandler(
        SECURITY_LOG_PATH,
        encoding="utf-8",
    )

    handler.setFormatter(SecurityJsonFormatter())

    logger.addHandler(handler)

    return logger


security_logger = _build_security_logger()


def security_event(
    event_name: str,
    *,
    outcome: str,
    request_id: str | None = None,
    actor_type: str | None = None,
    actor_id: str | int | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    source_ip: str | None = None,
    reason_code: str | None = None,
) -> None:
    security_logger.info(
        "security_event",
        extra={
            "event_name": _bounded(event_name, 80),
            "outcome": _bounded(outcome, 32),
            "request_id": _bounded(request_id, 64),
            "actor_type": _bounded(actor_type, 64),
            "actor_id": _bounded(actor_id, 128),
            "target_type": _bounded(target_type, 64),
            "target_id": _bounded(target_id, 128),
            "source_ip": _bounded(source_ip, 64),
            "reason_code": _bounded(reason_code, 128),
        },
    )
