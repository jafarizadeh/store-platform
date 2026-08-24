from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.payment_errors import (
    PaymentWebhookClaimLostError,
    PaymentWebhookReferenceUnavailableError,
)
from app.payments.orchestrator import (
    complete_payment_system,
    refresh_payment_status,
)
from app.payments.paypal_webhook import (
    PayPalWebhookAction,
    PayPalWebhookEvent,
)
from app.payments.provider import (
    PaymentProvider,
)
from app.repositories.payment_repository import (
    get_payment_attempt_by_provider_reference,
)
from app.services.payment_webhook_service import (
    PaymentWebhookClaimState,
    claim_payment_webhook_event,
    complete_payment_webhook_claim,
    release_payment_webhook_claim,
)


class PayPalWebhookProcessingState(StrEnum):
    PROCESSED = "processed"
    ALREADY_PROCESSED = "already_processed"
    IN_PROGRESS = "in_progress"


@dataclass(
    frozen=True,
    slots=True,
)
class PayPalWebhookProcessingOutcome:
    event_id: UUID
    state: PayPalWebhookProcessingState


def _release_claim_safely(
    db: Session,
    *,
    event_id: UUID,
    processing_token: UUID,
) -> None:
    try:
        release_payment_webhook_claim(
            db,
            event_id=event_id,
            processing_token=processing_token,
        )
    except PaymentWebhookClaimLostError:
        # A stale worker must never clear a
        # newer worker's lease.
        pass


def process_verified_paypal_webhook(
    db: Session,
    *,
    provider: PaymentProvider,
    event: PayPalWebhookEvent,
) -> PayPalWebhookProcessingOutcome:
    claim = claim_payment_webhook_event(
        db,
        provider=provider.name,
        provider_event_id=event.event_id,
        event_type=event.event_type,
        provider_reference=(event.provider_reference),
    )

    if claim.state == PaymentWebhookClaimState.ALREADY_PROCESSED:
        return PayPalWebhookProcessingOutcome(
            event_id=claim.event_id,
            state=(PayPalWebhookProcessingState.ALREADY_PROCESSED),
        )

    if claim.state == PaymentWebhookClaimState.IN_PROGRESS:
        return PayPalWebhookProcessingOutcome(
            event_id=claim.event_id,
            state=(PayPalWebhookProcessingState.IN_PROGRESS),
        )

    processing_token = claim.processing_token

    if processing_token is None:
        raise RuntimeError("Claimed webhook has no processing token.")

    try:
        if event.action == PayPalWebhookAction.IGNORE:
            complete_payment_webhook_claim(
                db,
                event_id=claim.event_id,
                processing_token=processing_token,
                payment_attempt_id=None,
            )

            return PayPalWebhookProcessingOutcome(
                event_id=claim.event_id,
                state=(PayPalWebhookProcessingState.PROCESSED),
            )

        provider_reference = event.provider_reference

        if provider_reference is None:
            raise (PaymentWebhookReferenceUnavailableError)

        attempt = get_payment_attempt_by_provider_reference(
            db,
            provider=provider.name,
            provider_reference=(provider_reference),
        )

        if attempt is None:
            raise (PaymentWebhookReferenceUnavailableError)

        attempt_id = attempt.id

        if event.action == PayPalWebhookAction.CAPTURE:
            complete_payment_system(
                db,
                attempt_id=attempt_id,
                provider=provider,
            )

        elif event.action == PayPalWebhookAction.REFRESH:
            refresh_payment_status(
                db,
                attempt_id=attempt_id,
                provider=provider,
                user_id=None,
            )

        else:
            raise RuntimeError("Unsupported PayPal webhook action.")

        complete_payment_webhook_claim(
            db,
            event_id=claim.event_id,
            processing_token=processing_token,
            payment_attempt_id=attempt_id,
        )

        return PayPalWebhookProcessingOutcome(
            event_id=claim.event_id,
            state=(PayPalWebhookProcessingState.PROCESSED),
        )

    except Exception:
        _release_claim_safely(
            db,
            event_id=claim.event_id,
            processing_token=processing_token,
        )
        raise
