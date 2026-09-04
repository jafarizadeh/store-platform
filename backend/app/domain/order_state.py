from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


_ALLOWED_TRANSITIONS: dict[
    OrderStatus,
    frozenset[OrderStatus],
] = {
    OrderStatus.PENDING: frozenset(
        {
            OrderStatus.PAID,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
        }
    ),
    OrderStatus.PAID: frozenset(
        {
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        }
    ),
    OrderStatus.PROCESSING: frozenset(
        {
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        }
    ),
    OrderStatus.SHIPPED: frozenset(
        {
            OrderStatus.DELIVERED,
            OrderStatus.REFUNDED,
        }
    ),
    OrderStatus.DELIVERED: frozenset(
        {
            OrderStatus.REFUNDED,
        }
    ),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.EXPIRED: frozenset(),
    OrderStatus.REFUNDED: frozenset(),
}


def is_order_transition_allowed(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> bool:
    return target_status in _ALLOWED_TRANSITIONS[current_status]
