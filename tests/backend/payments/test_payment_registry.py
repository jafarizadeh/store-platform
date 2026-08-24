from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.payments.paypal import (
    PayPalProvider,
)
from app.payments.registry import (
    create_payment_provider_registry,
)


def _database_url() -> str:
    return "postgresql+psycopg://test"


def _paypal_secret() -> str:
    return f"test-{uuid4().hex}"


def test_paypal_is_disabled_by_default():
    config = Settings(
        _env_file=None,
        database_url=_database_url(),
        paypal_enabled=False,
    )

    registry = create_payment_provider_registry(config)

    try:
        assert registry.get("paypal") is None
    finally:
        registry.close()


@pytest.mark.parametrize(
    (
        "environment",
        "expected_base_url",
    ),
    [
        (
            "sandbox",
            "https://api-m.sandbox.paypal.com",
        ),
        (
            "live",
            "https://api-m.paypal.com",
        ),
    ],
)
def test_paypal_registry_uses_allowlisted_environment(
    environment: str,
    expected_base_url: str,
):
    config = Settings(
        _env_file=None,
        database_url=_database_url(),
        paypal_enabled=True,
        paypal_environment=environment,
        paypal_client_id=(f"client-{uuid4().hex}"),
        paypal_client_secret=(_paypal_secret()),
        paypal_return_url=("https://store.example/checkout/paypal/return"),
        paypal_cancel_url=("https://store.example/checkout/paypal/cancel"),
        paypal_webhook_id=("WH-BYNET-TEST"),
    )

    registry = create_payment_provider_registry(config)

    try:
        provider = registry.get("paypal")

        assert isinstance(
            provider,
            PayPalProvider,
        )

        assert provider._http.base_url == httpx.URL(expected_base_url)

        assert provider._http.follow_redirects is False

    finally:
        registry.close()


def test_enabled_paypal_requires_credentials():
    with pytest.raises(
        ValidationError,
        match="PAYPAL_CLIENT_ID",
    ):
        Settings(
            _env_file=None,
            database_url=_database_url(),
            paypal_enabled=True,
            paypal_client_id=None,
            paypal_client_secret=None,
            paypal_return_url=None,
            paypal_cancel_url=None,
            paypal_webhook_id=("WH-BYNET-TEST"),
        )


def test_paypal_callback_url_rejects_embedded_credentials():
    with pytest.raises(
        ValidationError,
        match="PAYPAL_RETURN_URL",
    ):
        Settings(
            _env_file=None,
            database_url=_database_url(),
            paypal_enabled=True,
            paypal_client_id=(f"client-{uuid4().hex}"),
            paypal_client_secret=(_paypal_secret()),
            paypal_return_url=("https://user:password@store.example/paypal/return"),
            paypal_cancel_url=("https://store.example/paypal/cancel"),
            paypal_webhook_id=("WH-BYNET-TEST"),
        )
