import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.order import OrderLineSnapshot
from app.domain.order_errors import (
    IdempotencyConflictError,
    InvalidOrderTransitionError,
    MixedCurrencyError,
    OrderNotFoundError,
    OrderQuantityLimitError,
)
from app.domain.order_event import (
    OrderActorType,
    OrderEventSource,
    OrderEventType,
)
from app.domain.order_state import (
    OrderStatus,
    is_order_transition_allowed,
)
from app.models.order import Order
from app.repositories.order_event_repository import (
    append_order_event,
)
from app.repositories.order_repository import (
    create_order,
    get_due_pending_orders_for_update,
    get_order_by_idempotency_key,
    get_order_for_update,
    list_orders_for_user,
)
from app.repositories.user_repository import (
    get_user_by_id_for_update,
)
from app.schemas.order import OrderCreate
from app.services.inventory_service import (
    release_inventory,
    reserve_inventory,
)

MAX_ORDER_QUANTITY_PER_OFFER = 100


def _aggregate_quantities(
    request: OrderCreate,
) -> dict[int, int]:
    quantities: dict[int, int] = defaultdict(int)

    for item in request.items:
        quantities[item.offer_id] += item.quantity

    return dict(quantities)


def _validate_quantity_limits(
    quantities: dict[int, int],
) -> None:
    for offer_id, quantity in quantities.items():
        if quantity > MAX_ORDER_QUANTITY_PER_OFFER:
            raise OrderQuantityLimitError(
                offer_id=offer_id,
                requested_quantity=quantity,
                max_quantity=(MAX_ORDER_QUANTITY_PER_OFFER),
            )


def _request_fingerprint(
    quantities: dict[int, int],
) -> str:
    canonical_items = [
        {
            "offer_id": offer_id,
            "quantity": quantity,
        }
        for offer_id, quantity in sorted(quantities.items())
    ]

    payload = json.dumps(
        canonical_items,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def create_pending_order(
    db: Session,
    request: OrderCreate,
    *,
    user_id: UUID,
    idempotency_key: str,
) -> Order:
    requested_quantities = _aggregate_quantities(request)

    request_fingerprint = _request_fingerprint(requested_quantities)

    try:
        locked_user = get_user_by_id_for_update(
            db,
            user_id,
        )

        if locked_user is None:
            raise RuntimeError("Authenticated user no longer exists.")

        existing_order = get_order_by_idempotency_key(
            db,
            user_id=user_id,
            idempotency_key=(idempotency_key),
        )

        if existing_order is not None:
            if existing_order.request_fingerprint != request_fingerprint:
                raise (IdempotencyConflictError)

            db.commit()

            return existing_order

        _validate_quantity_limits(requested_quantities)

        offers = reserve_inventory(
            db,
            requested_quantities,
        )

        currencies = {offer.currency for offer in offers.values()}

        if len(currencies) != 1:
            raise MixedCurrencyError

        currency = currencies.pop()

        if currency is None:
            raise RuntimeError("Validated fixed-price offer has no currency.")

        lines: list[OrderLineSnapshot] = []

        for offer_id, quantity in sorted(requested_quantities.items()):
            offer = offers[offer_id]

            if offer.price_cents is None:
                raise RuntimeError("Validated fixed-price offer has no price.")

            lines.append(
                OrderLineSnapshot(
                    offer_id=offer.id,
                    product_name=(offer.product.name),
                    offer_name=offer.name,
                    sku=offer.sku,
                    fulfillment_type=(offer.fulfillment_type),
                    unit_price_cents=(offer.price_cents),
                    quantity=quantity,
                )
            )

        total_cents = sum(line.unit_price_cents * line.quantity for line in lines)

        reservation_expires_at = datetime.now(UTC) + timedelta(
            minutes=(settings.order_reservation_minutes)
        )

        order = create_order(
            db,
            user_id=user_id,
            idempotency_key=(idempotency_key),
            request_fingerprint=(request_fingerprint),
            reservation_expires_at=(reservation_expires_at),
            currency=currency,
            total_cents=total_cents,
            lines=lines,
        )

        append_order_event(
            db,
            order_id=order.id,
            event_type=(OrderEventType.ORDER_CREATED),
            actor_type=(OrderActorType.CUSTOMER),
            actor_id=str(user_id),
            source=(OrderEventSource.CHECKOUT),
            event_data={
                "status": order.status,
                "currency": order.currency,
                "total_cents": (order.total_cents),
            },
        )

        append_order_event(
            db,
            order_id=order.id,
            event_type=(OrderEventType.INVENTORY_RESERVED),
            actor_type=(OrderActorType.SYSTEM),
            actor_id=None,
            source=(OrderEventSource.ORDER_SERVICE),
            event_data={
                "items": [
                    {
                        "offer_id": offer_id,
                        "quantity": quantity,
                    }
                    for offer_id, quantity in sorted(requested_quantities.items())
                ]
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return order


def transition_order_status(
    db: Session,
    *,
    order_id: UUID,
    target_status: OrderStatus,
    actor_type: OrderActorType = (OrderActorType.SYSTEM),
    actor_id: str | None = None,
    source: OrderEventSource = (OrderEventSource.ORDER_SERVICE),
) -> Order:
    try:
        order = get_order_for_update(
            db,
            order_id=order_id,
        )

        if order is None:
            raise OrderNotFoundError(order_id)

        current_status = OrderStatus(order.status)

        if not is_order_transition_allowed(
            current_status,
            target_status,
        ):
            raise (
                InvalidOrderTransitionError(
                    current_status=(current_status.value),
                    target_status=(target_status.value),
                )
            )

        order.status = target_status.value

        append_order_event(
            db,
            order_id=order.id,
            event_type=(OrderEventType.ORDER_STATUS_CHANGED),
            actor_type=actor_type,
            actor_id=actor_id,
            source=source,
            event_data={
                "from_status": (current_status.value),
                "to_status": (target_status.value),
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return order


def expire_due_pending_orders(
    db: Session,
    *,
    current_time: datetime | None = None,
    batch_size: int = 100,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    if current_time is None:
        current_time = datetime.now(UTC)

    try:
        orders = get_due_pending_orders_for_update(
            db,
            current_time=current_time,
            limit=batch_size,
        )

        if not orders:
            db.commit()
            return 0

        # Critical payment/expiry race boundary:
        #
        # The Order rows above are already locked.
        # Re-read payment state now, inside the same
        # transaction, before releasing inventory.
        #
        # CREATED is externally ambiguous: the provider
        # may have accepted a request whose response was
        # lost.
        #
        # PENDING is also externally unresolved: customer
        # or provider confirmation may still succeed.
        from app.repositories.payment_repository import (
            get_order_ids_with_unresolved_payment_attempts,
        )

        protected_order_ids = get_order_ids_with_unresolved_payment_attempts(
            db,
            order_ids=[order.id for order in orders],
        )

        orders = [order for order in orders if order.id not in protected_order_ids]

        if not orders:
            db.commit()
            return 0

        released_quantities: dict[
            int,
            int,
        ] = defaultdict(int)

        for order in orders:
            for item in order.items:
                released_quantities[item.offer_id] += item.quantity

        # Lock all affected offer rows once,
        # in deterministic ID order, before
        # changing any stock.
        release_inventory(
            db,
            dict(released_quantities),
        )

        for order in orders:
            if order.status != OrderStatus.PENDING.value:
                raise RuntimeError("Locked expiry candidate is no longer pending.")

            order.status = OrderStatus.EXPIRED.value

            append_order_event(
                db,
                order_id=order.id,
                event_type=(OrderEventType.ORDER_STATUS_CHANGED),
                actor_type=(OrderActorType.SYSTEM),
                actor_id=None,
                source=(OrderEventSource.RESERVATION_EXPIRY),
                event_data={
                    "from_status": "pending",
                    "to_status": "expired",
                },
            )

            append_order_event(
                db,
                order_id=order.id,
                event_type=(OrderEventType.INVENTORY_RELEASED),
                actor_type=(OrderActorType.SYSTEM),
                actor_id=None,
                source=(OrderEventSource.RESERVATION_EXPIRY),
                event_data={
                    "reason": ("reservation_expired"),
                    "items": [
                        {
                            "offer_id": (item.offer_id),
                            "quantity": (item.quantity),
                        }
                        for item in sorted(
                            order.items,
                            key=lambda item: item.offer_id,
                        )
                    ],
                },
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return len(orders)


def get_orders_for_user(
    db: Session,
    user_id: UUID,
) -> list[Order]:
    return list_orders_for_user(
        db,
        user_id,
    )
