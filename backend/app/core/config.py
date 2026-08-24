from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import (
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ByNET API"

    order_reservation_minutes: int = 15

    database_url: SecretStr

    allowed_hosts: list[str] = [
        "127.0.0.1",
        "localhost",
        "testserver",
    ]

    paypal_enabled: bool = False

    paypal_environment: Literal[
        "sandbox",
        "live",
    ] = "sandbox"

    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None

    paypal_return_url: str | None = None
    paypal_cancel_url: str | None = None
    paypal_webhook_id: str | None = None

    paypal_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=30.0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_paypal_configuration(
        self,
    ) -> Self:
        if not self.paypal_enabled:
            return self

        missing: list[str] = []

        if not (self.paypal_client_id and self.paypal_client_id.strip()):
            missing.append("PAYPAL_CLIENT_ID")

        if (
            self.paypal_client_secret is None
            or not self.paypal_client_secret.get_secret_value().strip()
        ):
            missing.append("PAYPAL_CLIENT_SECRET")

        if not (self.paypal_return_url and self.paypal_return_url.strip()):
            missing.append("PAYPAL_RETURN_URL")

        if not (self.paypal_cancel_url and self.paypal_cancel_url.strip()):
            missing.append("PAYPAL_CANCEL_URL")

        if not (self.paypal_webhook_id and self.paypal_webhook_id.strip()):
            missing.append("PAYPAL_WEBHOOK_ID")

        if self.paypal_webhook_id is not None:
            webhook_id = self.paypal_webhook_id.strip()

            if len(webhook_id) > 200 or "\x00" in webhook_id:
                raise ValueError("PAYPAL_WEBHOOK_ID is invalid.")

        if missing:
            raise ValueError(
                "PayPal is enabled but required "
                "configuration is missing: " + ", ".join(missing)
            )

        for field_name, value in (
            (
                "PAYPAL_RETURN_URL",
                self.paypal_return_url,
            ),
            (
                "PAYPAL_CANCEL_URL",
                self.paypal_cancel_url,
            ),
        ):
            if value is None:
                continue

            parsed = urlparse(value)

            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError(
                    f"{field_name} must be a "
                    "valid HTTP(S) URL without "
                    "embedded credentials."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
