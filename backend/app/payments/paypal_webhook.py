from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from app.domain.payment_errors import (
    InvalidPaymentWebhookEventError,
)

_MAX_WEBHOOK_BODY_BYTES = 1_048_576

_PAYPAL_REFERENCE_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")

_CAPTURE_EVENTS = {
    "PAYMENT.CAPTURE.PENDING",
    "PAYMENT.CAPTURE.COMPLETED",
    "PAYMENT.CAPTURE.DENIED",
}


class PayPalWebhookAction(StrEnum):
    CAPTURE = "capture"
    REFRESH = "refresh"
    IGNORE = "ignore"


@dataclass(
    frozen=True,
    slots=True,
)
class PayPalWebhookEvent:
    event_id: str
    event_type: str
    provider_reference: str | None
    action: PayPalWebhookAction


def _required_text(
    value,
    *,
    max_length: int,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_length
        or "\x00" in value
    ):
        raise InvalidPaymentWebhookEventError

    return value


def _provider_reference(
    value,
) -> str:
    value = _required_text(
        value,
        max_length=64,
    )

    if not _PAYPAL_REFERENCE_RE.fullmatch(value):
        raise InvalidPaymentWebhookEventError

    return value


def _resource(
    payload: dict,
) -> dict:
    resource = payload.get("resource")

    if not isinstance(resource, dict):
        raise InvalidPaymentWebhookEventError

    return resource


def _capture_order_reference(
    resource: dict,
) -> str:
    supplementary = resource.get("supplementary_data")

    if not isinstance(
        supplementary,
        dict,
    ):
        raise InvalidPaymentWebhookEventError

    related_ids = supplementary.get("related_ids")

    if not isinstance(
        related_ids,
        dict,
    ):
        raise InvalidPaymentWebhookEventError

    return _provider_reference(related_ids.get("order_id"))


def parse_paypal_webhook_event(
    raw_body: bytes,
) -> PayPalWebhookEvent:
    if (
        not isinstance(raw_body, bytes)
        or not raw_body
        or len(raw_body) > _MAX_WEBHOOK_BODY_BYTES
    ):
        raise InvalidPaymentWebhookEventError

    try:
        payload = json.loads(raw_body)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise (InvalidPaymentWebhookEventError) from exc

    if not isinstance(payload, dict):
        raise InvalidPaymentWebhookEventError

    event_id = _required_text(
        payload.get("id"),
        max_length=200,
    )

    event_type = _required_text(
        payload.get("event_type"),
        max_length=120,
    )

    if event_type == "CHECKOUT.ORDER.APPROVED":
        reference = _provider_reference(_resource(payload).get("id"))

        return PayPalWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            provider_reference=reference,
            action=(PayPalWebhookAction.CAPTURE),
        )

    if event_type == "CHECKOUT.PAYMENT-APPROVAL.REVERSED":
        reference = _provider_reference(_resource(payload).get("order_id"))

        return PayPalWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            provider_reference=reference,
            action=(PayPalWebhookAction.REFRESH),
        )

    if event_type in _CAPTURE_EVENTS:
        reference = _capture_order_reference(_resource(payload))

        return PayPalWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            provider_reference=reference,
            action=(PayPalWebhookAction.REFRESH),
        )

    # Authenticated but unrelated PayPal
    # webhook. The HTTP layer will safely
    # acknowledge and deduplicate it without
    # touching payment state.
    return PayPalWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        provider_reference=None,
        action=PayPalWebhookAction.IGNORE,
    )
