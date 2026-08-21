from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
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
    statement = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )

    if category is not None:
        statement = statement.where(Product.category == category)

    return list(db.scalars(statement).all())


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

    statement = select(Product).where(
        Product.slug == slug,
        Product.is_active.is_(True),
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product
