from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    offer_id: int = Field(
        ge=1,
    )

    quantity: int = Field(
        ge=1,
        le=100,
    )


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(
        min_length=1,
        max_length=100,
    )


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    offer_id: int
    product_name: str
    offer_name: str
    sku: str
    fulfillment_type: str
    unit_price_cents: int
    quantity: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    order_number: str
    status: str
    currency: str
    total_cents: int
    created_at: datetime
    items: list[OrderItemResponse]
