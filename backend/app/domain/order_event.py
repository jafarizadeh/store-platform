from enum import StrEnum


class OrderEventType(StrEnum):
    AUDIT_BASELINE_CREATED = "audit_baseline_created"
    ORDER_CREATED = "order_created"
    INVENTORY_RESERVED = "inventory_reserved"
    INVENTORY_RELEASED = "inventory_released"
    ORDER_STATUS_CHANGED = "order_status_changed"


class OrderActorType(StrEnum):
    CUSTOMER = "customer"
    SYSTEM = "system"


class OrderEventSource(StrEnum):
    CHECKOUT = "checkout"
    MIGRATION = "migration"
    ORDER_SERVICE = "order_service"
    RESERVATION_EXPIRY = "reservation_expiry"
