from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.payment import (
    PaymentAttemptStatus,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentInitiationRequest:
    payment_id: UUID
    attempt_id: UUID
    order_id: UUID
    order_number: str
    amount_cents: int
    currency: str


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentCompletionRequest:
    payment_id: UUID
    attempt_id: UUID
    order_id: UUID
    order_number: str
    amount_cents: int
    currency: str
    provider_reference: str


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentCompletionResult:
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentStatusRequest:
    payment_id: UUID
    attempt_id: UUID
    order_id: UUID
    order_number: str
    amount_cents: int
    currency: str
    provider_reference: str


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentStatusResult:
    status: PaymentAttemptStatus
    provider_reference: str
    failure_code: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class PaymentInitiationResult:
    status: PaymentAttemptStatus
    provider_reference: str | None
    approval_url: str | None = None
    failure_code: str | None = None


class PaymentProvider(Protocol):
    name: str

    def initiate_payment(
        self,
        request: PaymentInitiationRequest,
    ) -> PaymentInitiationResult: ...

    def complete_payment(
        self,
        request: PaymentCompletionRequest,
    ) -> PaymentCompletionResult: ...

    def get_payment_status(
        self,
        request: PaymentStatusRequest,
    ) -> PaymentStatusResult: ...
