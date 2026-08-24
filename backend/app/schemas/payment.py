from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.domain.payment import (
    PaymentAttemptStatus,
)


class PaymentCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    order_id: UUID


class PaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    order_id: UUID
    status: str
    amount_cents: int
    currency: str
    created_at: datetime
    updated_at: datetime


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    provider: str = Field(
        min_length=1,
        max_length=40,
    )


class PaymentInitiationResponse(BaseModel):
    attempt_id: UUID
    status: PaymentAttemptStatus
    provider_reference: str | None
    approval_url: str | None
    failure_code: str | None


class PaymentCompletionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    provider: str = Field(
        min_length=1,
        max_length=40,
    )


class PaymentCompletionResponse(BaseModel):
    attempt_id: UUID
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None


class PaymentStatusRefreshCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    provider: str = Field(
        min_length=1,
        max_length=40,
    )


class PaymentStatusRefreshResponse(BaseModel):
    attempt_id: UUID
    order_id: UUID
    order_number: str
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None
