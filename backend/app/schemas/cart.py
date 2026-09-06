from typing import Literal

from pydantic import BaseModel, Field


class CartValidationItemRequest(BaseModel):
    offer_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=100)


class CartValidationRequest(BaseModel):
    items: list[CartValidationItemRequest] = Field(
        min_length=1,
        max_length=100,
    )


CartValidationIssue = Literal[
    "offer_unavailable",
    "quote_required",
    "insufficient_stock",
    "quantity_limit_exceeded",
]


class CartValidationItemResponse(BaseModel):
    offer_id: int
    requested_quantity: int
    issue: CartValidationIssue | None

    product_slug: str | None
    product_name: str | None
    offer_name: str | None
    sku: str | None
    fulfillment_type: str | None

    unit_price_cents: int | None
    currency: str | None

    image_path: str | None

    available_quantity: int | None
    max_quantity: int | None


class CartValidationResponse(BaseModel):
    valid: bool
    currency: str | None
    subtotal_cents: int | None
    mixed_currency: bool
    items: list[CartValidationItemResponse]
