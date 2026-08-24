import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _paypal_settings(
    **overrides,
):
    values = {
        "database_url": ("postgresql://test:test@127.0.0.1/test"),
        "paypal_enabled": True,
        "paypal_environment": "sandbox",
        "paypal_client_id": "test-client",
        "paypal_client_secret": "test-secret",
        "paypal_return_url": ("http://127.0.0.1/checkout/payment/return"),
        "paypal_cancel_url": ("http://127.0.0.1/checkout/payment/cancel"),
        "paypal_webhook_id": "WH-BYNET-TEST",
    }

    values.update(overrides)

    return Settings(**values)


def test_enabled_paypal_requires_webhook_id():
    with pytest.raises(
        ValidationError,
        match="PAYPAL_WEBHOOK_ID",
    ):
        _paypal_settings(
            paypal_webhook_id=None,
        )


def test_enabled_paypal_rejects_blank_webhook_id():
    with pytest.raises(
        ValidationError,
        match="PAYPAL_WEBHOOK_ID",
    ):
        _paypal_settings(
            paypal_webhook_id="   ",
        )


def test_enabled_paypal_accepts_webhook_id():
    settings = _paypal_settings()

    assert settings.paypal_webhook_id == "WH-BYNET-TEST"


def test_disabled_paypal_does_not_require_webhook_id():
    settings = Settings(
        database_url=("postgresql://test:test@127.0.0.1/test"),
        paypal_enabled=False,
    )

    assert settings.paypal_enabled is False
