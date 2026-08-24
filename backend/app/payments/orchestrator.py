from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.payment import (
    PaymentAttemptStatus,
)
from app.domain.payment_errors import (
    InvalidPaymentProviderResultError,
    PaymentProviderUnavailableError,
)
from app.payments.provider import (
    PaymentCompletionResult,
    PaymentInitiationResult,
    PaymentProvider,
    PaymentStatusResult,
)
from app.services.payment_service import (
    prepare_provider_completion,
    prepare_provider_initiation,
    prepare_provider_status_check,
    reconcile_provider_completion,
    reconcile_provider_initiation,
    reconcile_provider_status,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentInitiationOutcome:
    attempt_id: UUID
    status: PaymentAttemptStatus
    provider_reference: str | None
    approval_url: str | None
    failure_code: str | None


def initiate_payment(
    db: Session,
    *,
    payment_id: UUID,
    user_id: UUID,
    provider: PaymentProvider,
    idempotency_key: str,
) -> PaymentInitiationOutcome:
    request, existing = prepare_provider_initiation(
        db,
        payment_id=payment_id,
        user_id=user_id,
        provider=provider.name,
        idempotency_key=idempotency_key,
    )

    if existing["status"] != PaymentAttemptStatus.CREATED:
        return PaymentInitiationOutcome(
            attempt_id=request.attempt_id,
            status=existing["status"],
            provider_reference=(existing["provider_reference"]),
            approval_url=(existing["approval_url"]),
            failure_code=(existing["failure_code"]),
        )

    # There must be no active SQLAlchemy
    # transaction at this boundary.
    if db.in_transaction():
        raise RuntimeError("Database transaction remained open before provider call.")

    try:
        result = provider.initiate_payment(request)
    except InvalidPaymentProviderResultError:
        raise
    except Exception as exc:
        # Ambiguous external outcome:
        # leave attempt CREATED so retry can
        # reuse the same stable attempt_id.
        raise PaymentProviderUnavailableError from exc

    if not isinstance(
        result,
        PaymentInitiationResult,
    ):
        raise InvalidPaymentProviderResultError

    reconciled = reconcile_provider_initiation(
        db,
        attempt_id=request.attempt_id,
        result=result,
    )

    return PaymentInitiationOutcome(
        attempt_id=reconciled.id,
        status=PaymentAttemptStatus(reconciled.status),
        provider_reference=(reconciled.provider_reference),
        approval_url=(reconciled.approval_url),
        failure_code=(reconciled.failure_code),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentStatusOutcome:
    attempt_id: UUID
    order_id: UUID
    order_number: str
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None


def refresh_payment_status(
    db: Session,
    *,
    attempt_id: UUID,
    provider: PaymentProvider,
    user_id: UUID | None = None,
) -> PaymentStatusOutcome:
    request, existing = prepare_provider_status_check(
        db,
        attempt_id=attempt_id,
        provider=provider.name,
        user_id=user_id,
    )

    if existing is not None:
        return PaymentStatusOutcome(
            attempt_id=request.attempt_id,
            order_id=request.order_id,
            order_number=request.order_number,
            status=existing["status"],
            provider_reference=(existing["provider_reference"]),
            failure_code=(existing["failure_code"]),
        )

    if db.in_transaction():
        raise RuntimeError(
            "Database transaction remained open before provider status call."
        )

    try:
        result = provider.get_payment_status(request)
    except InvalidPaymentProviderResultError:
        raise
    except Exception as exc:
        raise PaymentProviderUnavailableError from exc

    if not isinstance(
        result,
        PaymentStatusResult,
    ):
        raise InvalidPaymentProviderResultError

    reconciled = reconcile_provider_status(
        db,
        attempt_id=request.attempt_id,
        result=result,
    )

    return PaymentStatusOutcome(
        attempt_id=reconciled.id,
        order_id=request.order_id,
        order_number=request.order_number,
        status=PaymentAttemptStatus(reconciled.status),
        provider_reference=(reconciled.provider_reference),
        failure_code=(reconciled.failure_code),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentCompletionOutcome:
    attempt_id: UUID
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None


def _complete_payment(
    db: Session,
    *,
    attempt_id: UUID,
    user_id: UUID | None,
    provider: PaymentProvider,
) -> PaymentCompletionOutcome:
    request, existing = prepare_provider_completion(
        db,
        attempt_id=attempt_id,
        user_id=user_id,
        provider=provider.name,
    )

    if existing is not None:
        return PaymentCompletionOutcome(
            attempt_id=request.attempt_id,
            status=existing["status"],
            provider_reference=(existing["provider_reference"]),
            failure_code=(existing["failure_code"]),
        )

    if db.in_transaction():
        raise RuntimeError(
            "Database transaction remained open before provider completion call."
        )

    try:
        result = provider.complete_payment(request)
    except InvalidPaymentProviderResultError:
        raise
    except Exception as exc:
        # External completion outcome may be
        # ambiguous. Keep the attempt PENDING
        # so status reconciliation can recover.
        raise PaymentProviderUnavailableError from exc

    if not isinstance(
        result,
        PaymentCompletionResult,
    ):
        raise InvalidPaymentProviderResultError

    reconciled = reconcile_provider_completion(
        db,
        attempt_id=request.attempt_id,
        result=result,
    )

    return PaymentCompletionOutcome(
        attempt_id=reconciled.id,
        status=PaymentAttemptStatus(reconciled.status),
        provider_reference=(reconciled.provider_reference),
        failure_code=(reconciled.failure_code),
    )


def complete_payment(
    db: Session,
    *,
    attempt_id: UUID,
    user_id: UUID,
    provider: PaymentProvider,
) -> PaymentCompletionOutcome:
    """Customer-authenticated completion path."""
    return _complete_payment(
        db,
        attempt_id=attempt_id,
        user_id=user_id,
        provider=provider,
    )


def complete_payment_system(
    db: Session,
    *,
    attempt_id: UUID,
    provider: PaymentProvider,
) -> PaymentCompletionOutcome:
    """Trusted server-side completion path."""
    return _complete_payment(
        db,
        attempt_id=attempt_id,
        user_id=None,
        provider=provider,
    )
