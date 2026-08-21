import inspect
import json
import logging

from app.core.audit import SecurityJsonFormatter, security_event


def make_record() -> logging.LogRecord:
    record = logging.LogRecord(
        name="bynet.security",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="security_event",
        args=(),
        exc_info=None,
    )

    record.event_name = "login_failed"
    record.outcome = "failure"
    record.request_id = "abc123"
    record.actor_type = "user"
    record.actor_id = "42"
    record.target_type = "session"
    record.target_id = "session-1"
    record.source_ip = "192.168.1.150"
    record.reason_code = "invalid_credentials"

    return record


def test_security_formatter_outputs_valid_json() -> None:
    payload = json.loads(SecurityJsonFormatter().format(make_record()))

    assert payload["logger"] == "bynet.security"
    assert payload["event"] == "login_failed"
    assert payload["outcome"] == "failure"
    assert payload["request_id"] == "abc123"
    assert payload["source_ip"] == "192.168.1.150"
    assert payload["reason_code"] == "invalid_credentials"


def test_security_formatter_has_expected_fields_only() -> None:
    payload = json.loads(SecurityJsonFormatter().format(make_record()))

    allowed_fields = {
        "timestamp",
        "level",
        "logger",
        "event",
        "outcome",
        "request_id",
        "actor_type",
        "actor_id",
        "target_type",
        "target_id",
        "source_ip",
        "reason_code",
    }

    assert set(payload) <= allowed_fields


def test_security_event_api_has_no_sensitive_parameters() -> None:
    parameters = set(inspect.signature(security_event).parameters)

    forbidden = {
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "request_body",
        "card_number",
        "cvv",
    }

    assert parameters.isdisjoint(forbidden)
