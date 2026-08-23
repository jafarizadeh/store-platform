from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.order_errors import (
    InsufficientStockError,
    MixedCurrencyError,
    OfferRequiresQuoteError,
    OfferUnavailableError,
)
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import create_pending_order

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    request: OrderCreate,
    db: DatabaseSession,
):
    try:
        return create_pending_order(
            db,
            request,
        )

    except OfferUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "offer_unavailable",
                "offer_id": exc.offer_id,
            },
        ) from exc

    except OfferRequiresQuoteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "quote_required",
                "offer_id": exc.offer_id,
            },
        ) from exc

    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "insufficient_stock",
                "offer_id": exc.offer_id,
                "requested_quantity": (exc.requested_quantity),
                "available_quantity": (exc.available_quantity),
            },
        ) from exc

    except MixedCurrencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "mixed_currency",
            },
        ) from exc
