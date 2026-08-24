from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.catalog_repository import (
    get_active_product_by_slug,
    list_active_products,
)
from app.schemas.product import ProductResponse

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "",
    response_model=list[ProductResponse],
)
def list_products(
    db: DatabaseSession,
    category: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=80,
        ),
    ] = None,
    product_type: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=20,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
        ),
    ] = 0,
):
    return list_active_products(
        db,
        category=category,
        product_type=product_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{slug}",
    response_model=ProductResponse,
)
def get_product(
    slug: str,
    db: DatabaseSession,
):
    if not 1 <= len(slug) <= 120:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product = get_active_product_by_slug(
        db,
        slug,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
