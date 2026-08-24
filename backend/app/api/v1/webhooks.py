from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.payment_errors import (
    InvalidPaymentProviderResultError,
    InvalidPaymentWebhookEventError,
    PaymentDomainError,
    PaymentProviderResultConflictError,
    PaymentProviderUnavailableError,
    PaymentWebhookEventConflictError,
    PaymentWebhookReferenceUnavailableError,
)
from app.payments.paypal_webhook import (
    parse_paypal_webhook_event,
)
from app.payments.registry import (
    PaymentProviderRegistry,
    get_payment_provider_registry,
)
from app.services.paypal_webhook_handler import (
    PayPalWebhookProcessingState,
    process_verified_paypal_webhook,
)

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


ProviderRegistry = Annotated[
    PaymentProviderRegistry,
    Depends(get_payment_provider_registry),
]


async def _read_raw_webhook_body(
    request: Request,
) -> bytes:
    return await request.body()


RawWebhookBody = Annotated[
    bytes,
    Depends(_read_raw_webhook_body),
]


_REQUIRED_PAYPAL_HEADERS = {
    "transmission_id": b"paypal-transmission-id",
    "transmission_time": b"paypal-transmission-time",
    "transmission_sig": b"paypal-transmission-sig",
    "cert_url": b"paypal-cert-url",
    "auth_algo": b"paypal-auth-algo",
}


def _single_raw_header(
    request: Request,
    *,
    header_name: bytes,
) -> str:
    values = [
        value
        for name, value in request.scope.get(
            "headers",
            [],
        )
        if name.lower() == header_name
    ]

    if len(values) != 1:
        raise InvalidPaymentWebhookEventError

    try:
        value = values[0].decode("latin-1")
    except UnicodeDecodeError as exc:
        raise (InvalidPaymentWebhookEventError) from exc

    if not value or "\x00" in value:
        raise InvalidPaymentWebhookEventError

    return value


def _paypal_verification_headers(
    request: Request,
) -> dict[str, str]:
    return {
        key: _single_raw_header(
            request,
            header_name=header_name,
        )
        for key, header_name in _REQUIRED_PAYPAL_HEADERS.items()
    }


@router.post(
    "/paypal",
    status_code=status.HTTP_200_OK,
)
def receive_paypal_webhook(
    request: Request,
    raw_body: RawWebhookBody,
    db: DatabaseSession,
    providers: ProviderRegistry,
):
    content_type = (
        request.headers.get(
            "content-type",
            "",
        )
        .partition(";")[0]
        .strip()
        .lower()
    )

    if content_type != "application/json":
        raise HTTPException(
            status_code=(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
            detail={
                "code": "invalid_webhook_content_type",
            },
        )

    try:
        verification_headers = _paypal_verification_headers(request)
    except InvalidPaymentWebhookEventError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_paypal_webhook",
            },
        ) from exc

    provider = providers.get("paypal")

    if provider is None:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "paypal_webhook_unavailable",
            },
        )

    verifier = getattr(
        provider,
        "verify_webhook_signature",
        None,
    )

    if not callable(verifier):
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "paypal_webhook_unavailable",
            },
        )

    try:
        verified = verifier(
            transmission_id=(verification_headers["transmission_id"]),
            transmission_time=(verification_headers["transmission_time"]),
            cert_url=(verification_headers["cert_url"]),
            auth_algo=(verification_headers["auth_algo"]),
            transmission_sig=(verification_headers["transmission_sig"]),
            raw_webhook_event=raw_body,
        )

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "paypal_verification_unavailable",
            },
        ) from exc

    except InvalidPaymentProviderResultError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "paypal_verification_error",
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "paypal_verification_unavailable",
            },
        ) from exc

    if verified is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_paypal_webhook_signature",
            },
        )

    # Parsing happens only after authenticity
    # has been established.
    try:
        event = parse_paypal_webhook_event(raw_body)
    except InvalidPaymentWebhookEventError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_paypal_webhook",
            },
        ) from exc

    try:
        outcome = process_verified_paypal_webhook(
            db,
            provider=provider,
            event=event,
        )

    except PaymentWebhookEventConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "payment_webhook_event_conflict",
            },
        ) from exc

    except PaymentWebhookReferenceUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "payment_webhook_reference_unavailable",
            },
            headers={
                "Retry-After": "5",
            },
        ) from exc

    except PaymentProviderUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "payment_provider_unavailable",
            },
            headers={
                "Retry-After": "5",
            },
        ) from exc

    except (
        InvalidPaymentProviderResultError,
        PaymentProviderResultConflictError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "payment_provider_error",
            },
        ) from exc

    except PaymentDomainError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "payment_webhook_retry",
            },
            headers={
                "Retry-After": "5",
            },
        ) from exc

    if outcome.state == PayPalWebhookProcessingState.IN_PROGRESS:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": "payment_webhook_in_progress",
            },
            headers={
                "Retry-After": "5",
            },
        )

    return {
        "status": "accepted",
    }
