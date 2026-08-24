from typing import Annotated

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
from app.core.idempotency import (
    is_valid_idempotency_key,
)
from app.db.session import get_db
from app.domain.order_errors import (
    IdempotencyConflictError,
    InsufficientStockError,
    MixedCurrencyError,
    OfferRequiresQuoteError,
    OfferUnavailableError,
    OrderQuantityLimitError,
)
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
)
from app.services.auth_service import (
    AuthenticatedSession,
)
from app.services.order_service import (
    create_pending_order,
    get_orders_for_user,
)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

Authenticated = Annotated[
    AuthenticatedSession,
    Depends(require_authenticated_session),
]

IdempotencyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
    ),
]


@router.get(
    "",
    response_model=list[OrderResponse],
)
def list_orders(
    db: DatabaseSession,
    authenticated: Authenticated,
):
    return get_orders_for_user(
        db,
        authenticated.user.id,
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    request: OrderCreate,
    db: DatabaseSession,
    authenticated: Authenticated,
    idempotency_key: IdempotencyHeader = None,
):
    if not is_valid_idempotency_key(idempotency_key):
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": "invalid_idempotency_key",
            },
        )

    try:
        return create_pending_order(
            db,
            request,
            user_id=(authenticated.user.id),
            idempotency_key=(idempotency_key),
        )

    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "code": "idempotency_conflict",
            },
        ) from exc

    except OfferUnavailableError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "code": "offer_unavailable",
                "offer_id": exc.offer_id,
            },
        ) from exc

    except OfferRequiresQuoteError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "code": "quote_required",
                "offer_id": exc.offer_id,
            },
        ) from exc

    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "code": "insufficient_stock",
                "offer_id": exc.offer_id,
                "requested_quantity": (exc.requested_quantity),
                "available_quantity": (exc.available_quantity),
            },
        ) from exc

    except OrderQuantityLimitError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": "quantity_limit_exceeded",
                "offer_id": exc.offer_id,
                "requested_quantity": (exc.requested_quantity),
                "max_quantity": exc.max_quantity,
            },
        ) from exc

    except MixedCurrencyError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail={
                "code": "mixed_currency",
            },
        ) from exc
