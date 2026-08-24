import json
from urllib.parse import parse_qs
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import pytest

from app.domain.payment import (
    PaymentAttemptStatus,
)
from app.domain.payment_errors import (
    InvalidPaymentProviderResultError,
)
from app.payments.paypal import (
    PayPalProvider,
)
from app.payments.provider import (
    PaymentCompletionRequest,
    PaymentInitiationRequest,
    PaymentStatusRequest,
)

BASE_URL = "https://api-m.sandbox.paypal.com"

PAYPAL_ORDER_ID = "PAYPALORDER12345"

APPROVAL_URL = "https://www.sandbox.paypal.com/checkoutnow?token=PAYPALORDER12345"


def _order_payload(
    *,
    status: str,
    amount: str = "12.34",
    currency: str = "EUR",
):
    payload = {
        "id": PAYPAL_ORDER_ID,
        "status": status,
        "purchase_units": [
            {
                "amount": {
                    "currency_code": currency,
                    "value": amount,
                }
            }
        ],
        "links": [
            {
                "rel": "payer-action",
                "href": APPROVAL_URL,
                "method": "GET",
            }
        ],
    }

    if status == "COMPLETED":
        unit = payload["purchase_units"][0]

        unit["payments"] = {
            "captures": [
                {
                    "id": ("CAPTURE123456789"),
                    "status": "COMPLETED",
                    "amount": {
                        "currency_code": currency,
                        "value": amount,
                    },
                }
            ]
        }

    return payload


def _provider(
    handler,
    *,
    webhook_id: str | None = "WH-TEST-BYNET",
):
    transport = httpx.MockTransport(handler)

    client = httpx.Client(
        base_url=BASE_URL,
        transport=transport,
        timeout=5.0,
    )

    provider = PayPalProvider(
        client_id="sandbox-client-id",
        client_secret=(f"sandbox-{uuid4().hex}"),
        return_url=("http://127.0.0.1/checkout/paypal/return"),
        cancel_url=("http://127.0.0.1/checkout/paypal/cancel"),
        http_client=client,
        webhook_id=webhook_id,
    )

    return provider, client


def _token_response():
    return httpx.Response(
        200,
        json={
            "access_token": "sandbox-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )


def test_paypal_create_order_maps_to_pending():
    attempt_id = uuid4()
    order_id = uuid4()

    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(request)

        if request.url.path == "/v1/oauth2/token":
            assert request.method == "POST"

            authorization = request.headers.get("Authorization")

            assert authorization is not None
            assert authorization.startswith("Basic ")

            form = parse_qs(request.content.decode())

            assert form == {"grant_type": ["client_credentials"]}

            return _token_response()

        assert request.method == "POST"
        assert request.url.path == "/v2/checkout/orders"

        assert request.headers["PayPal-Request-Id"] == str(attempt_id)

        assert request.headers["Authorization"] == "Bearer sandbox-token"

        body = json.loads(request.content)

        assert body["intent"] == "CAPTURE"

        unit = body["purchase_units"][0]

        assert unit["reference_id"] == str(order_id)

        assert unit["amount"] == {
            "currency_code": "EUR",
            "value": "12.34",
        }

        context = body["payment_source"]["paypal"]["experience_context"]

        assert context["return_url"] == ("http://127.0.0.1/checkout/paypal/return")

        return httpx.Response(
            201,
            json=_order_payload(status="CREATED"),
        )

    provider, client = _provider(handler)

    try:
        result = provider.initiate_payment(
            PaymentInitiationRequest(
                payment_id=uuid4(),
                attempt_id=attempt_id,
                order_id=order_id,
                order_number=("BY-2026-00000123"),
                amount_cents=1234,
                currency="EUR",
            )
        )
    finally:
        client.close()

    assert result.status == PaymentAttemptStatus.PENDING
    assert result.provider_reference == PAYPAL_ORDER_ID
    assert result.approval_url == APPROVAL_URL

    assert len(calls) == 2


def test_paypal_capture_maps_completed_to_success():
    attempt_id = uuid4()

    token_calls = 0

    def handler(
        request: httpx.Request,
    ):
        nonlocal token_calls

        if request.url.path == "/v1/oauth2/token":
            token_calls += 1
            return _token_response()

        assert request.method == "POST"

        assert request.url.path == (f"/v2/checkout/orders/{PAYPAL_ORDER_ID}/capture")

        expected_request_id = str(
            uuid5(
                NAMESPACE_URL,
                (f"bynet:paypal:capture:{attempt_id}"),
            )
        )

        assert request.headers["PayPal-Request-Id"] == expected_request_id

        return httpx.Response(
            201,
            json=_order_payload(status="COMPLETED"),
        )

    provider, client = _provider(handler)

    try:
        result = provider.complete_payment(
            PaymentCompletionRequest(
                payment_id=uuid4(),
                attempt_id=attempt_id,
                order_id=uuid4(),
                order_number=("BY-2026-00000124"),
                amount_cents=1234,
                currency="EUR",
                provider_reference=(PAYPAL_ORDER_ID),
            )
        )
    finally:
        client.close()

    assert result.status == PaymentAttemptStatus.SUCCEEDED

    assert result.provider_reference == PAYPAL_ORDER_ID

    assert token_calls == 1


def test_paypal_status_maps_approved_to_pending():
    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        assert request.method == "GET"

        assert request.url.path == (f"/v2/checkout/orders/{PAYPAL_ORDER_ID}")

        return httpx.Response(
            200,
            json=_order_payload(status="APPROVED"),
        )

    provider, client = _provider(handler)

    try:
        result = provider.get_payment_status(
            PaymentStatusRequest(
                payment_id=uuid4(),
                attempt_id=uuid4(),
                order_id=uuid4(),
                order_number=("BY-2026-00000125"),
                amount_cents=1234,
                currency="EUR",
                provider_reference=(PAYPAL_ORDER_ID),
            )
        )
    finally:
        client.close()

    assert result.status == PaymentAttemptStatus.PENDING


def test_paypal_reuses_cached_oauth_token():
    token_calls = 0

    def handler(
        request: httpx.Request,
    ):
        nonlocal token_calls

        if request.url.path == "/v1/oauth2/token":
            token_calls += 1
            return _token_response()

        if request.method == "POST":
            return httpx.Response(
                201,
                json=_order_payload(status="CREATED"),
            )

        return httpx.Response(
            200,
            json=_order_payload(status="APPROVED"),
        )

    provider, client = _provider(handler)

    attempt_id = uuid4()

    try:
        initiated = provider.initiate_payment(
            PaymentInitiationRequest(
                payment_id=uuid4(),
                attempt_id=attempt_id,
                order_id=uuid4(),
                order_number=("BY-2026-00000126"),
                amount_cents=1234,
                currency="EUR",
            )
        )

        assert initiated.provider_reference is not None

        provider.get_payment_status(
            PaymentStatusRequest(
                payment_id=uuid4(),
                attempt_id=attempt_id,
                order_id=uuid4(),
                order_number=("BY-2026-00000126"),
                amount_cents=1234,
                currency="EUR",
                provider_reference=(initiated.provider_reference),
            )
        )
    finally:
        client.close()

    assert token_calls == 1


@pytest.mark.parametrize(
    (
        "amount",
        "currency",
    ),
    [
        ("12.35", "EUR"),
        ("12.34", "USD"),
    ],
)
def test_paypal_rejects_provider_amount_mismatch(
    amount: str,
    currency: str,
):
    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        return httpx.Response(
            201,
            json=_order_payload(
                status="CREATED",
                amount=amount,
                currency=currency,
            ),
        )

    provider, client = _provider(handler)

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.initiate_payment(
                PaymentInitiationRequest(
                    payment_id=uuid4(),
                    attempt_id=uuid4(),
                    order_id=uuid4(),
                    order_number=("BY-2026-00000127"),
                    amount_cents=1234,
                    currency="EUR",
                )
            )
    finally:
        client.close()


def test_paypal_rejects_untrusted_approval_url():
    payload = _order_payload(status="CREATED")

    payload["links"] = [
        {
            "rel": "payer-action",
            "href": ("https://paypal.com.evil.example/steal"),
        }
    ]

    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        return httpx.Response(
            201,
            json=payload,
        )

    provider, client = _provider(handler)

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.initiate_payment(
                PaymentInitiationRequest(
                    payment_id=uuid4(),
                    attempt_id=uuid4(),
                    order_id=uuid4(),
                    order_number=("BY-2026-00000128"),
                    amount_cents=1234,
                    currency="EUR",
                )
            )
    finally:
        client.close()


def _raw_webhook_event() -> bytes:
    # Deliberate whitespace verifies that
    # PayPal receives the original event
    # bytes without event re-serialization.
    return (
        b"{\n"
        b'  "id": "WH-EVENT-123",\n'
        b'  "event_type": '
        b'"CHECKOUT.ORDER.APPROVED",\n'
        b'  "resource": {'
        b'"id": "PAYPALORDER12345"}\n'
        b"}"
    )


def _webhook_event():
    return {
        "id": "WH-EVENT-123",
        "event_type": ("CHECKOUT.ORDER.APPROVED"),
        "resource": {
            "id": PAYPAL_ORDER_ID,
        },
    }


def test_paypal_webhook_verification_success():
    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(request)

        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        assert request.method == "POST"

        assert request.url.path == ("/v1/notifications/verify-webhook-signature")

        assert request.headers["Authorization"] == "Bearer sandbox-token"

        assert (b'"webhook_event":' + _raw_webhook_event()) in request.content

        body = json.loads(request.content)

        assert body == {
            "auth_algo": "SHA256withRSA",
            "cert_url": (
                "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-123"
            ),
            "transmission_id": "TX-123",
            "transmission_sig": "signature-value",
            "transmission_time": "2026-08-24T20:00:00Z",
            "webhook_id": "WH-TEST-BYNET",
            "webhook_event": _webhook_event(),
        }

        return httpx.Response(
            200,
            json={
                "verification_status": "SUCCESS",
            },
        )

    provider, client = _provider(
        handler,
    )

    try:
        verified = provider.verify_webhook_signature(
            transmission_id="TX-123",
            transmission_time=("2026-08-24T20:00:00Z"),
            cert_url=("https://api.sandbox.paypal.com/v1/notifications/certs/CERT-123"),
            auth_algo="SHA256withRSA",
            transmission_sig=("signature-value"),
            raw_webhook_event=_raw_webhook_event(),
        )
    finally:
        client.close()

    assert verified is True
    assert len(calls) == 2


def test_paypal_webhook_verification_failure():
    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        return httpx.Response(
            200,
            json={
                "verification_status": "FAILURE",
            },
        )

    provider, client = _provider(
        handler,
    )

    try:
        verified = provider.verify_webhook_signature(
            transmission_id="TX-124",
            transmission_time=("2026-08-24T20:00:00Z"),
            cert_url=("https://api.sandbox.paypal.com/v1/notifications/certs/CERT-124"),
            auth_algo="SHA256withRSA",
            transmission_sig="signature",
            raw_webhook_event=_raw_webhook_event(),
        )
    finally:
        client.close()

    assert verified is False


def test_paypal_webhook_rejects_untrusted_cert_url():
    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(request)

        raise AssertionError("No provider request expected.")

    provider, client = _provider(
        handler,
    )

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.verify_webhook_signature(
                transmission_id="TX-125",
                transmission_time=("2026-08-24T20:00:00Z"),
                cert_url=("https://paypal.com.evil.example/cert"),
                auth_algo="SHA256withRSA",
                transmission_sig="signature",
                raw_webhook_event=_raw_webhook_event(),
            )
    finally:
        client.close()

    assert calls == []


def test_paypal_webhook_requires_webhook_id():
    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(request)

        raise AssertionError("No provider request expected.")

    provider, client = _provider(
        handler,
        webhook_id=None,
    )

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.verify_webhook_signature(
                transmission_id="TX-126",
                transmission_time=("2026-08-24T20:00:00Z"),
                cert_url=(
                    "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-126"
                ),
                auth_algo="SHA256withRSA",
                transmission_sig="signature",
                raw_webhook_event=_raw_webhook_event(),
            )
    finally:
        client.close()

    assert calls == []


def test_paypal_webhook_rejects_invalid_raw_event():
    calls = []

    def handler(
        request: httpx.Request,
    ):
        calls.append(request)

        raise AssertionError("No provider request expected.")

    provider, client = _provider(
        handler,
    )

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.verify_webhook_signature(
                transmission_id="TX-127",
                transmission_time=("2026-08-24T20:00:00Z"),
                cert_url=(
                    "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-127"
                ),
                auth_algo="SHA256withRSA",
                transmission_sig="signature",
                raw_webhook_event=(b'{"broken":'),
            )
    finally:
        client.close()

    assert calls == []


def test_paypal_completed_order_with_pending_capture_stays_pending():
    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        payload = _order_payload(
            status="COMPLETED",
        )

        payload["purchase_units"][0]["payments"]["captures"][0]["status"] = "PENDING"

        return httpx.Response(
            200,
            json=payload,
        )

    provider, client = _provider(
        handler,
    )

    try:
        result = provider.get_payment_status(
            PaymentStatusRequest(
                payment_id=uuid4(),
                attempt_id=uuid4(),
                order_id=uuid4(),
                order_number=("BY-2026-00000129"),
                amount_cents=1234,
                currency="EUR",
                provider_reference=(PAYPAL_ORDER_ID),
            )
        )
    finally:
        client.close()

    assert result.status == PaymentAttemptStatus.PENDING


def test_paypal_completed_order_without_capture_is_rejected():
    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        payload = _order_payload(
            status="COMPLETED",
        )

        payload["purchase_units"][0].pop("payments")

        return httpx.Response(
            200,
            json=payload,
        )

    provider, client = _provider(
        handler,
    )

    try:
        with pytest.raises(InvalidPaymentProviderResultError):
            provider.get_payment_status(
                PaymentStatusRequest(
                    payment_id=uuid4(),
                    attempt_id=uuid4(),
                    order_id=uuid4(),
                    order_number=("BY-2026-00000130"),
                    amount_cents=1234,
                    currency="EUR",
                    provider_reference=(PAYPAL_ORDER_ID),
                )
            )
    finally:
        client.close()


def test_paypal_capture_retry_reuses_same_request_id():
    attempt_id = uuid4()

    capture_request_ids = []

    def handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return _token_response()

        assert request.method == "POST"

        capture_request_ids.append(request.headers["PayPal-Request-Id"])

        return httpx.Response(
            201,
            json=_order_payload(
                status="COMPLETED",
            ),
        )

    provider, client = _provider(
        handler,
    )

    request = PaymentCompletionRequest(
        payment_id=uuid4(),
        attempt_id=attempt_id,
        order_id=uuid4(),
        order_number="BY-2026-00000131",
        amount_cents=1234,
        currency="EUR",
        provider_reference=(PAYPAL_ORDER_ID),
    )

    try:
        first = provider.complete_payment(request)

        second = provider.complete_payment(request)
    finally:
        client.close()

    expected = str(
        uuid5(
            NAMESPACE_URL,
            (f"bynet:paypal:capture:{attempt_id}"),
        )
    )

    assert first.status == PaymentAttemptStatus.SUCCEEDED

    assert second.status == PaymentAttemptStatus.SUCCEEDED

    assert capture_request_ids == [
        expected,
        expected,
    ]

    assert len(expected) == 36
    assert expected != str(attempt_id)
