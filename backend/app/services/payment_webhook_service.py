from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.domain.payment_errors import (
    InvalidPaymentWebhookEventError,
    PaymentWebhookClaimLostError,
    PaymentWebhookEventConflictError,
)
from app.repositories.payment_repository import (
    get_payment_webhook_event_by_provider_id_for_update,
    get_payment_webhook_event_for_update,
    insert_payment_webhook_event_claim,
)

DEFAULT_WEBHOOK_LEASE_SECONDS = 300


class PaymentWebhookClaimState(StrEnum):
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    ALREADY_PROCESSED = "already_processed"


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentWebhookClaim:
    event_id: UUID
    state: PaymentWebhookClaimState
    processing_token: UUID | None


def _validated_text(
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
        raise InvalidPaymentWebhookEventError

    return value


def _validated_provider_reference(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    return _validated_text(
        value,
        max_length=200,
    )


def _claim_time(
    current_time: datetime | None,
) -> datetime:
    value = current_time if current_time is not None else datetime.now(UTC)

    if value.tzinfo is None:
        raise InvalidPaymentWebhookEventError

    return value


def claim_payment_webhook_event(
    db: Session,
    *,
    provider: str,
    provider_event_id: str,
    event_type: str,
    provider_reference: str | None,
    lease_seconds: int = (DEFAULT_WEBHOOK_LEASE_SECONDS),
    current_time: datetime | None = None,
) -> PaymentWebhookClaim:
    normalized_provider = _validated_text(
        provider.strip().lower(),
        max_length=40,
    )

    provider_event_id = _validated_text(
        provider_event_id,
        max_length=200,
    )

    event_type = _validated_text(
        event_type,
        max_length=120,
    )

    provider_reference = _validated_provider_reference(
        provider_reference,
    )

    if not isinstance(lease_seconds, int) or lease_seconds < 1 or lease_seconds > 3600:
        raise InvalidPaymentWebhookEventError

    now = _claim_time(current_time)

    token = uuid4()

    try:
        created_id = insert_payment_webhook_event_claim(
            db,
            provider=normalized_provider,
            provider_event_id=(provider_event_id),
            event_type=event_type,
            provider_reference=(provider_reference),
            processing_token=token,
            processing_started_at=now,
        )

        if created_id is not None:
            db.commit()

            return PaymentWebhookClaim(
                event_id=created_id,
                state=(PaymentWebhookClaimState.CLAIMED),
                processing_token=token,
            )

        event = get_payment_webhook_event_by_provider_id_for_update(
            db,
            provider=normalized_provider,
            provider_event_id=(provider_event_id),
        )

        if event is None:
            raise PaymentWebhookEventConflictError

        if (
            event.event_type != event_type
            or event.provider_reference != provider_reference
        ):
            raise PaymentWebhookEventConflictError

        if event.processed_at is not None:
            event_id = event.id

            db.commit()

            return PaymentWebhookClaim(
                event_id=event_id,
                state=(PaymentWebhookClaimState.ALREADY_PROCESSED),
                processing_token=None,
            )

        lease_cutoff = now - timedelta(
            seconds=lease_seconds,
        )

        if (
            event.processing_token is not None
            and event.processing_started_at is not None
            and event.processing_started_at > lease_cutoff
        ):
            event_id = event.id

            db.commit()

            return PaymentWebhookClaim(
                event_id=event_id,
                state=(PaymentWebhookClaimState.IN_PROGRESS),
                processing_token=None,
            )

        event.processing_token = token
        event.processing_started_at = now

        event_id = event.id

        db.commit()

        return PaymentWebhookClaim(
            event_id=event_id,
            state=(PaymentWebhookClaimState.CLAIMED),
            processing_token=token,
        )

    except Exception:
        db.rollback()
        raise


def release_payment_webhook_claim(
    db: Session,
    *,
    event_id: UUID,
    processing_token: UUID,
) -> None:
    try:
        event = get_payment_webhook_event_for_update(
            db,
            webhook_event_id=event_id,
        )

        if (
            event is None
            or event.processed_at is not None
            or event.processing_token != processing_token
        ):
            raise PaymentWebhookClaimLostError

        event.processing_token = None
        event.processing_started_at = None

        db.commit()

    except Exception:
        db.rollback()
        raise


def complete_payment_webhook_claim(
    db: Session,
    *,
    event_id: UUID,
    processing_token: UUID,
    payment_attempt_id: UUID | None,
    current_time: datetime | None = None,
) -> None:
    now = _claim_time(current_time)

    try:
        event = get_payment_webhook_event_for_update(
            db,
            webhook_event_id=event_id,
        )

        if (
            event is None
            or event.processed_at is not None
            or event.processing_token != processing_token
        ):
            raise PaymentWebhookClaimLostError

        event.payment_attempt_id = payment_attempt_id

        event.processed_at = now
        event.processing_token = None
        event.processing_started_at = None

        db.commit()

    except Exception:
        db.rollback()
        raise
