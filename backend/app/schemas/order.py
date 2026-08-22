from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int = Field(
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

    product_id: int
    product_name: str
    unit_price_cents: int
    quantity: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    status: str
    currency: str
    total_cents: int
    created_at: datetime
    items: list[OrderItemResponse]
