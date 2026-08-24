from uuid import UUID


class PaymentDomainError(Exception):
    """Base class for expected payment-domain failures."""


class PaymentOrderUnavailableError(PaymentDomainError):
    def __init__(
        self,
        order_id: UUID,
    ) -> None:
        self.order_id = order_id

        super().__init__("Order is unavailable for payment.")


class PaymentOrderNotPayableError(PaymentDomainError):
    def __init__(
        self,
        *,
        order_id: UUID,
        current_status: str,
        reason: str,
    ) -> None:
        self.order_id = order_id
        self.current_status = current_status
        self.reason = reason

        super().__init__("Order cannot be paid.")


class PaymentAttemptNotFoundError(PaymentDomainError):
    def __init__(
        self,
        attempt_id: UUID,
    ) -> None:
        self.attempt_id = attempt_id

        super().__init__("Payment attempt was not found.")


class PaymentNotFoundError(PaymentDomainError):
    def __init__(
        self,
        payment_id: UUID,
    ) -> None:
        self.payment_id = payment_id

        super().__init__("Payment was not found.")


class PaymentNotPendingError(PaymentDomainError):
    def __init__(
        self,
        *,
        payment_id: UUID,
        current_status: str,
    ) -> None:
        self.payment_id = payment_id
        self.current_status = current_status

        super().__init__("Payment is not pending.")


class InvalidPaymentProviderError(PaymentDomainError):
    """Raised for invalid provider identifiers."""


class InvalidPaymentIdempotencyKeyError(PaymentDomainError):
    """Raised for invalid payment-attempt idempotency keys."""


class PaymentAttemptIdempotencyConflictError(PaymentDomainError):
    """Raised when one attempt key is reused for another provider."""


class PaymentAttemptAlreadyActiveError(PaymentDomainError):
    def __init__(
        self,
        *,
        payment_id: UUID,
        attempt_id: UUID,
        current_status: str,
    ) -> None:
        self.payment_id = payment_id
        self.attempt_id = attempt_id
        self.current_status = current_status

        super().__init__("Payment already has an unresolved attempt.")


class PaymentProviderUnavailableError(PaymentDomainError):
    """Provider call failed with an ambiguous external result."""


class InvalidPaymentProviderResultError(PaymentDomainError):
    """Provider returned an unsupported or malformed initiation result."""


class PaymentProviderResultConflictError(PaymentDomainError):
    """A retry returned data conflicting with the stored provider result."""


class PaymentWebhookEventConflictError(PaymentDomainError):
    """A provider event ID was replayed with conflicting data."""


class PaymentWebhookClaimLostError(PaymentDomainError):
    """A webhook worker no longer owns the processing lease."""


class InvalidPaymentWebhookEventError(PaymentDomainError):
    """Webhook metadata is malformed or outside accepted limits."""


class PaymentWebhookReferenceUnavailableError(PaymentDomainError):
    """A verified webhook does not map to a known payment attempt."""
