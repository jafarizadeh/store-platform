class OrderDomainError(Exception):
    """Base class for expected order-domain failures."""


class ProductUnavailableError(OrderDomainError):
    def __init__(
        self,
        product_id: int,
    ) -> None:
        self.product_id = product_id

        super().__init__(f"Product {product_id} is unavailable.")


class InsufficientStockError(OrderDomainError):
    def __init__(
        self,
        *,
        product_id: int,
        requested_quantity: int,
        available_quantity: int,
    ) -> None:
        self.product_id = product_id
        self.requested_quantity = requested_quantity
        self.available_quantity = available_quantity

        super().__init__(f"Insufficient stock for product {product_id}.")


class MixedCurrencyError(OrderDomainError):
    """Raised when an order contains products in different currencies."""
