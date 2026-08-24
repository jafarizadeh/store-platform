from functools import lru_cache

import httpx

from app.core.config import (
    Settings,
    settings,
)
from app.payments.paypal import (
    PayPalProvider,
)
from app.payments.provider import (
    PaymentProvider,
)

_PAYPAL_API_BASE_URLS = {
    "sandbox": ("https://api-m.sandbox.paypal.com"),
    "live": ("https://api-m.paypal.com"),
}


class PaymentProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[
            str,
            PaymentProvider,
        ] = {}

    def register(
        self,
        provider: PaymentProvider,
    ) -> None:
        name = provider.name.strip().lower()

        if not name or len(name) > 40:
            raise ValueError("Invalid payment provider name.")

        if name in self._providers:
            raise ValueError("Payment provider is already registered.")

        self._providers[name] = provider

    def get(
        self,
        name: str,
    ) -> PaymentProvider | None:
        normalized = name.strip().lower()

        if not normalized or len(normalized) > 40:
            return None

        return self._providers.get(normalized)

    def close(self) -> None:
        for provider in self._providers.values():
            close = getattr(
                provider,
                "close",
                None,
            )

            if callable(close):
                close()


def create_payment_provider_registry(
    config: Settings,
) -> PaymentProviderRegistry:
    registry = PaymentProviderRegistry()

    if not config.paypal_enabled:
        return registry

    client_id = config.paypal_client_id

    secret = config.paypal_client_secret

    return_url = config.paypal_return_url
    cancel_url = config.paypal_cancel_url

    # Settings validation should make these
    # unreachable. Keep this as a hard internal
    # safety assertion rather than silently
    # constructing a partially configured
    # provider.
    if client_id is None or secret is None or return_url is None or cancel_url is None:
        raise RuntimeError("Validated PayPal configuration is incomplete.")

    base_url = _PAYPAL_API_BASE_URLS[config.paypal_environment]

    http_client = httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(config.paypal_timeout_seconds),
        follow_redirects=False,
    )

    try:
        provider = PayPalProvider(
            client_id=client_id,
            client_secret=(secret.get_secret_value()),
            return_url=return_url,
            cancel_url=cancel_url,
            http_client=http_client,
            webhook_id=config.paypal_webhook_id,
        )

        registry.register(provider)

    except Exception:
        http_client.close()
        raise

    return registry


@lru_cache
def get_payment_provider_registry() -> PaymentProviderRegistry:
    return create_payment_provider_registry(settings)


def close_payment_provider_registry() -> None:
    if get_payment_provider_registry.cache_info().currsize:
        registry = get_payment_provider_registry()

        registry.close()

    get_payment_provider_registry.cache_clear()
