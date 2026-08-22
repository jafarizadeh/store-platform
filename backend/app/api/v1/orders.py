from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.order_errors import (
    InsufficientStockError,
    MixedCurrencyError,
    ProductUnavailableError,
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
        order = create_pending_order(
            db,
            request,
        )

    except ProductUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "product_unavailable",
                "product_id": exc.product_id,
            },
        ) from exc

    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "insufficient_stock",
                "product_id": exc.product_id,
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

    return order
