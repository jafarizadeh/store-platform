import json

import pytest

from app.domain.payment_errors import (
    InvalidPaymentWebhookEventError,
)
from app.payments.paypal_webhook import (
    PayPalWebhookAction,
    parse_paypal_webhook_event,
)

ORDER_ID = "9P99943869582473S"


def _raw(
    payload: dict,
) -> bytes:
    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def test_paypal_approved_event_requests_capture():
    event = parse_paypal_webhook_event(
        _raw(
            {
                "id": "WH-APPROVED-1",
                "event_type": "CHECKOUT.ORDER.APPROVED",
                "resource": {
                    "id": ORDER_ID,
                },
            }
        )
    )

    assert event.provider_reference == ORDER_ID
    assert event.action == PayPalWebhookAction.CAPTURE


def test_paypal_capture_completed_requests_refresh():
    event = parse_paypal_webhook_event(
        _raw(
            {
                "id": "WH-CAPTURE-1",
                "event_type": "PAYMENT.CAPTURE.COMPLETED",
                "resource": {
                    "id": "CAPTURE123",
                    "supplementary_data": {
                        "related_ids": {
                            "order_id": ORDER_ID,
                        }
                    },
                },
            }
        )
    )

    assert event.provider_reference == ORDER_ID
    assert event.action == PayPalWebhookAction.REFRESH


def test_paypal_reversed_event_requests_refresh():
    event = parse_paypal_webhook_event(
        _raw(
            {
                "id": "WH-REVERSED-1",
                "event_type": ("CHECKOUT.PAYMENT-APPROVAL.REVERSED"),
                "resource": {
                    "order_id": ORDER_ID,
                },
            }
        )
    )

    assert event.provider_reference == ORDER_ID
    assert event.action == PayPalWebhookAction.REFRESH


def test_unrelated_paypal_event_is_ignored():
    event = parse_paypal_webhook_event(
        _raw(
            {
                "id": "WH-OTHER-1",
                "event_type": "CUSTOMER.SOMETHING",
                "resource": {},
            }
        )
    )

    assert event.provider_reference is None
    assert event.action == PayPalWebhookAction.IGNORE


def test_capture_event_without_order_id_is_rejected():
    with pytest.raises(InvalidPaymentWebhookEventError):
        parse_paypal_webhook_event(
            _raw(
                {
                    "id": "WH-BAD-1",
                    "event_type": "PAYMENT.CAPTURE.COMPLETED",
                    "resource": {"supplementary_data": {"related_ids": {}}},
                }
            )
        )
