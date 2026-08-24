from uuid import UUID


class OrderDomainError(Exception):
    """Base class for expected order-domain failures."""


class OfferUnavailableError(OrderDomainError):
    def __init__(
        self,
        offer_id: int,
    ) -> None:
        self.offer_id = offer_id

        super().__init__(f"Offer {offer_id} is unavailable.")


class OfferRequiresQuoteError(OrderDomainError):
    def __init__(
        self,
        offer_id: int,
    ) -> None:
        self.offer_id = offer_id

        super().__init__(f"Offer {offer_id} requires a quote.")


class InsufficientStockError(OrderDomainError):
    def __init__(
        self,
        *,
        offer_id: int,
        requested_quantity: int,
        available_quantity: int,
    ) -> None:
        self.offer_id = offer_id
        self.requested_quantity = requested_quantity
        self.available_quantity = available_quantity

        super().__init__(f"Insufficient stock for offer {offer_id}.")


class MixedCurrencyError(OrderDomainError):
    """Raised for fixed-price offers with mixed currencies."""


class OrderQuantityLimitError(OrderDomainError):
    def __init__(
        self,
        offer_id: int,
        requested_quantity: int,
        max_quantity: int,
    ) -> None:
        self.offer_id = offer_id
        self.requested_quantity = requested_quantity
        self.max_quantity = max_quantity

        super().__init__("Order quantity limit exceeded.")


class IdempotencyConflictError(OrderDomainError):
    """Raised when one key is reused for a different order request."""


class OrderNotFoundError(OrderDomainError):
    def __init__(
        self,
        order_id: UUID,
    ) -> None:
        self.order_id = order_id

        super().__init__(f"Order {order_id} was not found.")


class InvalidOrderTransitionError(OrderDomainError):
    def __init__(
        self,
        *,
        current_status: str,
        target_status: str,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status

        super().__init__(
            f"Invalid order status transition: {current_status} -> {target_status}."
        )
