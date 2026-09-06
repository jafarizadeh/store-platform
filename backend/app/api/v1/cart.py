from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.cart import (
    CartValidationRequest,
    CartValidationResponse,
)
from app.services.cart_service import (
    validate_cart,
)

router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/validate",
    response_model=CartValidationResponse,
)
def validate_cart_route(
    request: CartValidationRequest,
    db: DatabaseSession,
):
    return validate_cart(
        db,
        request,
    )
