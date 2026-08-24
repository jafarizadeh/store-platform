import json
import re
from decimal import Decimal
from threading import Lock
from time import monotonic
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from app.domain.payment import (
    PaymentAttemptStatus,
)
from app.domain.payment_errors import (
    InvalidPaymentProviderResultError,
)
from app.payments.provider import (
    PaymentCompletionRequest,
    PaymentCompletionResult,
    PaymentInitiationRequest,
    PaymentInitiationResult,
    PaymentStatusRequest,
    PaymentStatusResult,
)

_PAYPAL_REFERENCE_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")

_PENDING_PAYPAL_STATUSES = {
    "CREATED",
    "SAVED",
    "APPROVED",
    "PAYER_ACTION_REQUIRED",
}


class PayPalProvider:
    name = "paypal"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        return_url: str,
        cancel_url: str,
        http_client: httpx.Client,
        webhook_id: str | None = None,
    ) -> None:
        if not client_id:
            raise ValueError("PayPal client ID is required.")

        if not client_secret:
            raise ValueError("PayPal client secret is required.")

        if not return_url:
            raise ValueError("PayPal return URL is required.")

        if not cancel_url:
            raise ValueError("PayPal cancel URL is required.")

        self._client_id = client_id
        self._client_secret = client_secret
        self._return_url = return_url
        self._cancel_url = cancel_url
        self._http = http_client

        normalized_webhook_id = webhook_id.strip() if webhook_id else ""

        if len(normalized_webhook_id) > 200:
            raise ValueError("PayPal webhook ID is too long.")

        self._webhook_id = normalized_webhook_id or None

        self._token_lock = Lock()
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    def close(self) -> None:
        self._http.close()

    def initiate_payment(
        self,
        request: PaymentInitiationRequest,
    ) -> PaymentInitiationResult:
        access_token = self._get_access_token()

        response = self._http.post(
            "/v2/checkout/orders",
            headers={
                "Authorization": (f"Bearer {access_token}"),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Prefer": "return=representation",
                "PayPal-Request-Id": str(request.attempt_id),
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": str(request.order_id),
                        "custom_id": (request.order_number),
                        "amount": {
                            "currency_code": (request.currency),
                            "value": (self._format_amount(request.amount_cents)),
                        },
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "return_url": (self._return_url),
                            "cancel_url": (self._cancel_url),
                        }
                    }
                },
            },
        )

        response.raise_for_status()

        payload = self._json_object(response)

        provider_reference = self._provider_reference(payload)

        self._validate_amount(
            payload,
            amount_cents=request.amount_cents,
            currency=request.currency,
        )

        status = self._map_order_payment_status(
            payload,
            amount_cents=request.amount_cents,
            currency=request.currency,
        )

        approval_url = None

        if status == PaymentAttemptStatus.PENDING:
            approval_url = self._approval_url(payload)

            if approval_url is None:
                raise (InvalidPaymentProviderResultError)

        return PaymentInitiationResult(
            status=status,
            provider_reference=(provider_reference),
            approval_url=approval_url,
        )

    def complete_payment(
        self,
        request: PaymentCompletionRequest,
    ) -> PaymentCompletionResult:
        provider_reference = self._validate_provider_reference(
            request.provider_reference
        )

        access_token = self._get_access_token()

        response = self._http.post(
            (f"/v2/checkout/orders/{provider_reference}/capture"),
            headers={
                "Authorization": (f"Bearer {access_token}"),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Prefer": "return=representation",
                "PayPal-Request-Id": (self._capture_request_id(request.attempt_id)),
            },
            json={},
        )

        response.raise_for_status()

        payload = self._json_object(response)

        returned_reference = self._provider_reference(payload)

        if returned_reference != provider_reference:
            raise InvalidPaymentProviderResultError

        self._validate_amount(
            payload,
            amount_cents=request.amount_cents,
            currency=request.currency,
        )

        return PaymentCompletionResult(
            status=self._map_order_payment_status(
                payload,
                amount_cents=request.amount_cents,
                currency=request.currency,
            ),
            provider_reference=(returned_reference),
        )

    def get_payment_status(
        self,
        request: PaymentStatusRequest,
    ) -> PaymentStatusResult:
        provider_reference = self._validate_provider_reference(
            request.provider_reference
        )

        access_token = self._get_access_token()

        response = self._http.get(
            (f"/v2/checkout/orders/{provider_reference}"),
            headers={
                "Authorization": (f"Bearer {access_token}"),
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        payload = self._json_object(response)

        returned_reference = self._provider_reference(payload)

        if returned_reference != provider_reference:
            raise InvalidPaymentProviderResultError

        self._validate_amount(
            payload,
            amount_cents=request.amount_cents,
            currency=request.currency,
        )

        return PaymentStatusResult(
            status=self._map_order_payment_status(
                payload,
                amount_cents=request.amount_cents,
                currency=request.currency,
            ),
            provider_reference=(returned_reference),
        )

    def verify_webhook_signature(
        self,
        *,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
        raw_webhook_event: bytes,
    ) -> bool:
        if self._webhook_id is None:
            raise InvalidPaymentProviderResultError

        transmission_id = self._validate_webhook_header(
            transmission_id,
            max_length=200,
        )

        transmission_time = self._validate_webhook_header(
            transmission_time,
            max_length=100,
        )

        auth_algo = self._validate_webhook_header(
            auth_algo,
            max_length=100,
        )

        transmission_sig = self._validate_webhook_header(
            transmission_sig,
            max_length=4096,
        )

        cert_url = self._validate_paypal_https_url(
            cert_url,
        )

        if (
            not isinstance(
                raw_webhook_event,
                bytes,
            )
            or not raw_webhook_event
            or len(raw_webhook_event) > 1_048_576
        ):
            raise InvalidPaymentProviderResultError

        try:
            parsed_event = json.loads(
                raw_webhook_event,
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise (InvalidPaymentProviderResultError) from exc

        if not isinstance(
            parsed_event,
            dict,
        ):
            raise InvalidPaymentProviderResultError

        access_token = self._get_access_token()

        verification_fields = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": self._webhook_id,
        }

        envelope = json.dumps(
            verification_fields,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        # Preserve the original webhook event
        # bytes inside PayPal's verification
        # envelope rather than serializing the
        # event object again.
        verification_body = (
            envelope[:-1] + b',"webhook_event":' + raw_webhook_event + b"}"
        )

        response = self._http.post(
            ("/v1/notifications/verify-webhook-signature"),
            headers={
                "Authorization": (f"Bearer {access_token}"),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            content=verification_body,
        )

        response.raise_for_status()

        payload = self._json_object(
            response,
        )

        verification_status = payload.get("verification_status")

        if verification_status == "SUCCESS":
            return True

        if verification_status == "FAILURE":
            return False

        raise InvalidPaymentProviderResultError

    @staticmethod
    def _validate_webhook_header(
        value: str,
        *,
        max_length: int,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > max_length
            or "\x00" in value
        ):
            raise InvalidPaymentProviderResultError

        return value

    @staticmethod
    def _validate_paypal_https_url(
        value: str,
    ) -> str:
        if not isinstance(value, str) or not value or len(value) > 2000:
            raise InvalidPaymentProviderResultError

        parsed = urlparse(value)

        hostname = (parsed.hostname or "").lower()

        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or not (hostname == "paypal.com" or hostname.endswith(".paypal.com"))
        ):
            raise InvalidPaymentProviderResultError

        return value

    def _get_access_token(self) -> str:
        now = monotonic()

        if self._access_token is not None and now < self._access_token_expires_at:
            return self._access_token

        with self._token_lock:
            now = monotonic()

            if self._access_token is not None and now < self._access_token_expires_at:
                return self._access_token

            response = self._http.post(
                "/v1/oauth2/token",
                auth=httpx.BasicAuth(
                    self._client_id,
                    self._client_secret,
                ),
                headers={
                    "Accept": "application/json",
                    "Content-Type": ("application/x-www-form-urlencoded"),
                },
                data={
                    "grant_type": ("client_credentials"),
                },
            )

            response.raise_for_status()

            payload = self._json_object(response)

            access_token = payload.get("access_token")
            token_type = payload.get("token_type")
            expires_in = payload.get("expires_in")

            if (
                not isinstance(
                    access_token,
                    str,
                )
                or not access_token
                or not isinstance(
                    token_type,
                    str,
                )
                or token_type.lower() != "bearer"
                or not isinstance(
                    expires_in,
                    int,
                )
                or expires_in <= 0
            ):
                raise (InvalidPaymentProviderResultError)

            # Keep a safety margin so a token
            # cannot expire during an API call.
            usable_lifetime = max(
                1,
                expires_in - 60,
            )

            self._access_token = access_token
            self._access_token_expires_at = monotonic() + usable_lifetime

            return access_token

    @staticmethod
    def _capture_request_id(
        attempt_id: UUID,
    ) -> str:
        return str(
            uuid5(
                NAMESPACE_URL,
                (f"bynet:paypal:capture:{attempt_id}"),
            )
        )

    @staticmethod
    def _format_amount(
        amount_cents: int,
    ) -> str:
        if amount_cents <= 0:
            raise ValueError("Payment amount must be positive.")

        amount = Decimal(amount_cents) / Decimal(100)

        return f"{amount:.2f}"

    @staticmethod
    def _json_object(
        response: httpx.Response,
    ) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise (InvalidPaymentProviderResultError) from exc

        if not isinstance(payload, dict):
            raise InvalidPaymentProviderResultError

        return payload

    @classmethod
    def _provider_reference(
        cls,
        payload: dict,
    ) -> str:
        value = payload.get("id")

        if not isinstance(value, str):
            raise InvalidPaymentProviderResultError

        return cls._validate_provider_reference(value)

    @staticmethod
    def _validate_provider_reference(
        value: str,
    ) -> str:
        if not _PAYPAL_REFERENCE_RE.fullmatch(value):
            raise InvalidPaymentProviderResultError

        return value

    @classmethod
    def _map_order_payment_status(
        cls,
        payload: dict,
        *,
        amount_cents: int,
        currency: str,
    ) -> PaymentAttemptStatus:
        order_status = payload.get("status")

        if order_status != "COMPLETED":
            return cls._map_status(
                order_status,
            )

        units = payload.get("purchase_units")

        if (
            not isinstance(units, list)
            or len(units) != 1
            or not isinstance(
                units[0],
                dict,
            )
        ):
            raise InvalidPaymentProviderResultError

        payments = units[0].get("payments")

        if not isinstance(
            payments,
            dict,
        ):
            raise InvalidPaymentProviderResultError

        captures = payments.get("captures")

        # ByNET currently performs one full
        # CAPTURE-intent payment per order.
        # Multiple/partial captures are not an
        # accepted state for this payment flow.
        if (
            not isinstance(captures, list)
            or len(captures) != 1
            or not isinstance(
                captures[0],
                dict,
            )
        ):
            raise InvalidPaymentProviderResultError

        capture = captures[0]

        capture_id = capture.get("id")

        if not isinstance(
            capture_id,
            str,
        ):
            raise InvalidPaymentProviderResultError

        cls._validate_provider_reference(
            capture_id,
        )

        capture_amount = capture.get("amount")

        if not isinstance(
            capture_amount,
            dict,
        ):
            raise InvalidPaymentProviderResultError

        if capture_amount.get("currency_code") != currency or capture_amount.get(
            "value"
        ) != cls._format_amount(amount_cents):
            raise InvalidPaymentProviderResultError

        capture_status = capture.get("status")

        if capture_status == "COMPLETED":
            return PaymentAttemptStatus.SUCCEEDED

        if capture_status == "PENDING":
            return PaymentAttemptStatus.PENDING

        if capture_status in {
            "DECLINED",
            "FAILED",
        }:
            return PaymentAttemptStatus.FAILED

        # REFUNDED / PARTIALLY_REFUNDED and
        # any unknown future state must not
        # silently enter the purchase-success
        # state machine.
        raise InvalidPaymentProviderResultError

    @staticmethod
    def _map_status(
        value,
    ) -> PaymentAttemptStatus:
        if not isinstance(value, str):
            raise InvalidPaymentProviderResultError

        if value in _PENDING_PAYPAL_STATUSES:
            return PaymentAttemptStatus.PENDING

        if value == "COMPLETED":
            return PaymentAttemptStatus.SUCCEEDED

        if value == "VOIDED":
            return PaymentAttemptStatus.CANCELLED

        raise InvalidPaymentProviderResultError

    @staticmethod
    def _approval_url(
        payload: dict,
    ) -> str | None:
        links = payload.get("links")

        if not isinstance(links, list):
            raise InvalidPaymentProviderResultError

        for preferred_rel in (
            "payer-action",
            "approve",
        ):
            for link in links:
                if not isinstance(link, dict):
                    continue

                if link.get("rel") != preferred_rel:
                    continue

                href = link.get("href")

                if not isinstance(href, str):
                    raise (InvalidPaymentProviderResultError)

                parsed = urlparse(href)

                hostname = (parsed.hostname or "").lower()

                if parsed.scheme != "https" or not (
                    hostname == "paypal.com" or hostname.endswith(".paypal.com")
                ):
                    raise (InvalidPaymentProviderResultError)

                return href

        return None

    @classmethod
    def _validate_amount(
        cls,
        payload: dict,
        *,
        amount_cents: int,
        currency: str,
    ) -> None:
        units = payload.get("purchase_units")

        if (
            not isinstance(units, list)
            or len(units) != 1
            or not isinstance(
                units[0],
                dict,
            )
        ):
            raise InvalidPaymentProviderResultError

        amount = units[0].get("amount")

        if not isinstance(amount, dict):
            raise InvalidPaymentProviderResultError

        returned_currency = amount.get("currency_code")
        returned_value = amount.get("value")

        if returned_currency != currency or returned_value != cls._format_amount(
            amount_cents
        ):
            raise InvalidPaymentProviderResultError
