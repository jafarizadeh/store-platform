from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest
from sqlalchemy.orm import Session

from app.domain.payment_errors import (
    PaymentWebhookClaimLostError,
    PaymentWebhookEventConflictError,
)
from app.services.payment_webhook_service import (
    PaymentWebhookClaimState,
    claim_payment_webhook_event,
    complete_payment_webhook_claim,
    release_payment_webhook_claim,
)


def test_webhook_claim_release_and_complete(
    db_session: Session,
):
    now = datetime(
        2026,
        8,
        24,
        20,
        0,
        tzinfo=UTC,
    )

    first = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-CLAIM-1",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference="ORDER123",
        current_time=now,
    )

    assert first.state == PaymentWebhookClaimState.CLAIMED
    assert first.processing_token is not None

    duplicate = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-CLAIM-1",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference="ORDER123",
        current_time=(now + timedelta(seconds=1)),
    )

    assert duplicate.state == PaymentWebhookClaimState.IN_PROGRESS
    assert duplicate.processing_token is None

    release_payment_webhook_claim(
        db_session,
        event_id=first.event_id,
        processing_token=(first.processing_token),
    )

    reclaimed = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-CLAIM-1",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference="ORDER123",
        current_time=(now + timedelta(seconds=2)),
    )

    assert reclaimed.state == PaymentWebhookClaimState.CLAIMED
    assert reclaimed.processing_token is not None
    assert reclaimed.processing_token != first.processing_token

    complete_payment_webhook_claim(
        db_session,
        event_id=reclaimed.event_id,
        processing_token=(reclaimed.processing_token),
        payment_attempt_id=None,
        current_time=(now + timedelta(seconds=3)),
    )

    replay = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-CLAIM-1",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference="ORDER123",
        current_time=(now + timedelta(seconds=4)),
    )

    assert replay.state == PaymentWebhookClaimState.ALREADY_PROCESSED


def test_webhook_stale_lease_can_be_taken_over(
    db_session: Session,
):
    now = datetime(
        2026,
        8,
        24,
        20,
        0,
        tzinfo=UTC,
    )

    first = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-STALE-1",
        event_type=("PAYMENT.CAPTURE.COMPLETED"),
        provider_reference="ORDER456",
        current_time=now,
        lease_seconds=300,
    )

    second = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-STALE-1",
        event_type=("PAYMENT.CAPTURE.COMPLETED"),
        provider_reference="ORDER456",
        current_time=(now + timedelta(seconds=301)),
        lease_seconds=300,
    )

    assert second.state == PaymentWebhookClaimState.CLAIMED
    assert second.processing_token is not None
    assert second.processing_token != first.processing_token

    with pytest.raises(PaymentWebhookClaimLostError):
        release_payment_webhook_claim(
            db_session,
            event_id=first.event_id,
            processing_token=(first.processing_token),
        )


def test_webhook_event_id_conflict_is_rejected(
    db_session: Session,
):
    first = claim_payment_webhook_event(
        db_session,
        provider="paypal",
        provider_event_id="WH-CONFLICT-1",
        event_type=("CHECKOUT.ORDER.APPROVED"),
        provider_reference="ORDER789",
    )

    assert first.processing_token is not None

    with pytest.raises(PaymentWebhookEventConflictError):
        claim_payment_webhook_event(
            db_session,
            provider="paypal",
            provider_event_id=("WH-CONFLICT-1"),
            event_type=("PAYMENT.CAPTURE.COMPLETED"),
            provider_reference="ORDER789",
        )


def test_webhook_claim_is_atomic_under_concurrency(
    test_engine,
):
    from concurrent.futures import (
        ThreadPoolExecutor,
    )
    from threading import Barrier
    from uuid import uuid4

    from sqlalchemy import (
        delete,
        func,
        select,
    )
    from sqlalchemy.orm import Session

    from app.models.payment import (
        PaymentWebhookEvent,
    )

    event_id = "WH-RACE-" + uuid4().hex

    barrier = Barrier(2)

    def worker():
        with Session(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            barrier.wait(timeout=10)

            return claim_payment_webhook_event(
                db,
                provider="paypal",
                provider_event_id=event_id,
                event_type=("CHECKOUT.ORDER.APPROVED"),
                provider_reference=("RACEORDER123"),
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker) for _ in range(2)]

            results = [future.result(timeout=15) for future in futures]

        states = sorted(result.state.value for result in results)

        assert states == [
            "claimed",
            "in_progress",
        ]

        with Session(
            bind=test_engine,
            autoflush=False,
        ) as verify_db:
            count = verify_db.scalar(
                select(func.count())
                .select_from(PaymentWebhookEvent)
                .where(
                    PaymentWebhookEvent.provider == "paypal",
                    PaymentWebhookEvent.provider_event_id == event_id,
                )
            )

            assert count == 1

    finally:
        with Session(
            bind=test_engine,
            autoflush=False,
        ) as cleanup_db:
            cleanup_db.execute(
                delete(PaymentWebhookEvent).where(
                    PaymentWebhookEvent.provider == "paypal",
                    PaymentWebhookEvent.provider_event_id == event_id,
                )
            )

            cleanup_db.commit()
