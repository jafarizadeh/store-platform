from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    require_authenticated_session,
)
from app.db.session import get_db
from app.domain.payment_errors import (
    InvalidPaymentIdempotencyKeyError,
    InvalidPaymentProviderError,
    InvalidPaymentProviderResultError,
    PaymentAttemptAlreadyActiveError,
    PaymentAttemptIdempotencyConflictError,
    PaymentAttemptNotFoundError,
    PaymentNotFoundError,
    PaymentNotPendingError,
    PaymentOrderNotPayableError,
    PaymentOrderUnavailableError,
    PaymentProviderResultConflictError,
    PaymentProviderUnavailableError,
)
from app.payments.orchestrator import (
    complete_payment,
    initiate_payment,
    refresh_payment_status,
)
from app.payments.registry import (
    PaymentProviderRegistry,
    get_payment_provider_registry,
)
from app.schemas.payment import (
    PaymentCompletionCreate,
    PaymentCompletionResponse,
    PaymentCreate,
    PaymentInitiateRequest,
    PaymentInitiationResponse,
    PaymentResponse,
    PaymentStatusRefreshCreate,
    PaymentStatusRefreshResponse,
)
from app.services.auth_service import (
    AuthenticatedSession,
)
from app.services.payment_service import (
    prepare_payment,
)

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


Authenticated = Annotated[
    AuthenticatedSession,
    Depends(require_authenticated_session),
]


ProviderRegistry = Annotated[
    PaymentProviderRegistry,
    Depends(get_payment_provider_registry),
]


IdempotencyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
    ),
]


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
)
def create_or_get_payment(
    request: PaymentCreate,
    db: DatabaseSession,
    authenticated: Authenticated,
):
    try:
        return prepare_payment(
            db,
            order_id=request.order_id,
            user_id=authenticated.user.id,
        )

    except PaymentOrderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "payment_order_unavailable",
            },
        ) from exc

    except PaymentOrderNotPayableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_not_payable",
                "reason": exc.reason,
            },
        ) from exc


@router.post(
    "/{payment_id}/initiate",
    response_model=PaymentInitiationResponse,
    status_code=status.HTTP_200_OK,
)
def initiate_payment_api(
    payment_id: UUID,
    request: PaymentInitiateRequest,
    db: DatabaseSession,
    authenticated: Authenticated,
    providers: ProviderRegistry,
    idempotency_key: IdempotencyHeader = None,
):
    provider = providers.get(request.provider)

    if provider is None:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        )

    try:
        return initiate_payment(
            db,
            payment_id=payment_id,
            user_id=authenticated.user.id,
            provider=provider,
            idempotency_key=(idempotency_key or ""),
        )

    except InvalidPaymentIdempotencyKeyError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": "invalid_idempotency_key",
            },
        ) from exc

    except InvalidPaymentProviderError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        ) from exc

    except (
        PaymentNotFoundError,
        PaymentOrderUnavailableError,
    ) as exc:
        # Missing and other-user payments are
        # intentionally indistinguishable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "payment_unavailable",
            },
        ) from exc

    except PaymentOrderNotPayableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_not_payable",
                "reason": exc.reason,
            },
        ) from exc

    except PaymentNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "payment_not_pending",
            },
        ) from exc

    except PaymentAttemptIdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ("payment_idempotency_conflict"),
            },
        ) from exc

    except PaymentAttemptAlreadyActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": ("payment_attempt_already_active"),
                "attempt_id": str(exc.attempt_id),
                "status": exc.current_status,
            },
        ) from exc

    except PaymentProviderUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": ("payment_provider_unavailable"),
            },
        ) from exc

    except (
        InvalidPaymentProviderResultError,
        PaymentProviderResultConflictError,
    ) as exc:
        # Provider integration faults should
        # never expose raw provider data.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "payment_provider_error",
            },
        ) from exc


@router.post(
    "/attempts/{attempt_id}/complete",
    response_model=PaymentCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def complete_payment_api(
    attempt_id: UUID,
    request: PaymentCompletionCreate,
    db: DatabaseSession,
    authenticated: Authenticated,
    providers: ProviderRegistry,
):
    provider = providers.get(request.provider)

    if provider is None:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        )

    try:
        return complete_payment(
            db,
            attempt_id=attempt_id,
            user_id=authenticated.user.id,
            provider=provider,
        )

    except (
        PaymentAttemptNotFoundError,
        PaymentOrderUnavailableError,
    ) as exc:
        # Missing and other-user attempts must
        # remain indistinguishable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ("payment_attempt_unavailable"),
            },
        ) from exc

    except InvalidPaymentProviderError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        ) from exc

    except PaymentOrderNotPayableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_not_payable",
                "reason": exc.reason,
            },
        ) from exc

    except PaymentNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "payment_not_pending",
            },
        ) from exc

    except PaymentProviderUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": ("payment_provider_unavailable"),
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


@router.post(
    "/attempts/{attempt_id}/refresh",
    response_model=PaymentStatusRefreshResponse,
    status_code=status.HTTP_200_OK,
)
def refresh_payment_status_api(
    attempt_id: UUID,
    request: PaymentStatusRefreshCreate,
    db: DatabaseSession,
    authenticated: Authenticated,
    providers: ProviderRegistry,
):
    provider = providers.get(request.provider)

    if provider is None:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        )

    try:
        return refresh_payment_status(
            db,
            attempt_id=attempt_id,
            provider=provider,
            user_id=authenticated.user.id,
        )

    except (
        PaymentAttemptNotFoundError,
        PaymentOrderUnavailableError,
    ) as exc:
        # Missing and other-user attempts are
        # deliberately indistinguishable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ("payment_attempt_unavailable"),
            },
        ) from exc

    except InvalidPaymentProviderError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": ("unsupported_payment_provider"),
            },
        ) from exc

    except PaymentOrderNotPayableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "order_not_payable",
                "reason": exc.reason,
            },
        ) from exc

    except PaymentNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "payment_not_pending",
            },
        ) from exc

    except PaymentProviderUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail={
                "code": ("payment_provider_unavailable"),
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
