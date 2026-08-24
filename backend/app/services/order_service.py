import hashlib
import json
from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.order import OrderLineSnapshot
from app.domain.order_errors import (
    IdempotencyConflictError,
    MixedCurrencyError,
    OrderQuantityLimitError,
)
from app.domain.order_event import (
    OrderActorType,
    OrderEventSource,
    OrderEventType,
)
from app.models.order import Order
from app.repositories.order_event_repository import (
    append_order_event,
)
from app.repositories.order_repository import (
    create_order,
    get_order_by_idempotency_key,
    list_orders_for_user,
)
from app.repositories.user_repository import (
    get_user_by_id_for_update,
)
from app.schemas.order import OrderCreate
from app.services.inventory_service import (
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

        order = create_order(
            db,
            user_id=user_id,
            idempotency_key=(idempotency_key),
            request_fingerprint=(request_fingerprint),
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


def get_orders_for_user(
    db: Session,
    user_id: UUID,
) -> list[Order]:
    return list_orders_for_user(
        db,
        user_id,
    )
