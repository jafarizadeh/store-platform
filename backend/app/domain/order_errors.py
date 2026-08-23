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
    """Raised when an order contains fixed-price offers in different currencies."""
