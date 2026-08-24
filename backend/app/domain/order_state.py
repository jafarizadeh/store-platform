from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
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
