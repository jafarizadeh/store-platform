from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import uuid4

from factories.catalog import (
    create_product_offer,
)
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.domain.order_event import (
    OrderEventSource,
    OrderEventType,
)
from app.domain.order_state import (
    OrderStatus,
)
from app.models.order import Order
from app.models.product_offer import (
    ProductOffer,
)
from app.models.user import User
from app.repositories.order_event_repository import (
    list_order_events,
)
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
)
from app.services.order_service import (
    create_pending_order,
    expire_due_pending_orders,
    transition_order_status,
)

TEST_CREDENTIAL_HASH = hash_password("reservation-expiry-test-credential")


def _create_pending_order(
    db: Session,
    *,
    stock_quantity: int = 1,
) -> tuple[Order, ProductOffer]:
    suffix = uuid4().hex

    user = User(
        email=(f"reservation-expiry-{suffix}@example.com"),
        password_hash=(TEST_CREDENTIAL_HASH),
        is_active=True,
    )

    db.add(user)
    db.flush()

    _, offer = create_product_offer(
        db,
        slug=(f"reservation-expiry-{suffix}"),
        price_cents=1200,
        stock_quantity=stock_quantity,
    )

    db.commit()

    order = create_pending_order(
        db,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=1,
                )
            ]
        ),
        user_id=user.id,
        idempotency_key=(f"expiry-{uuid4().hex}"),
    )

    return order, offer


def test_pending_order_has_future_reservation_deadline(
    db_session: Session,
) -> None:
    before = datetime.now(UTC)

    order, _ = _create_pending_order(db_session)

    after = datetime.now(UTC)

    assert order.reservation_expires_at > before

    assert order.reservation_expires_at <= after + timedelta(minutes=16)


def test_expired_pending_order_releases_inventory_once(
    db_session: Session,
) -> None:
    order, offer = _create_pending_order(db_session)

    current_time = datetime.now(UTC)

    order.reservation_expires_at = current_time - timedelta(seconds=1)

    db_session.commit()

    db_session.refresh(offer)

    assert offer.stock_quantity == 0

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=current_time,
    )

    assert expired_count == 1

    db_session.refresh(order)
    db_session.refresh(offer)

    assert order.status == "expired"
    assert offer.stock_quantity == 1

    events = list_order_events(
        db_session,
        order_id=order.id,
    )

    assert [event.event_type for event in events[-2:]] == [
        OrderEventType.ORDER_STATUS_CHANGED,
        OrderEventType.INVENTORY_RELEASED,
    ]

    assert all(
        event.source == OrderEventSource.RESERVATION_EXPIRY for event in events[-2:]
    )

    assert events[-1].event_data == {
        "reason": "reservation_expired",
        "items": [
            {
                "offer_id": offer.id,
                "quantity": 1,
            }
        ],
    }

    second_count = expire_due_pending_orders(
        db_session,
        current_time=current_time,
    )

    assert second_count == 0

    db_session.refresh(offer)

    assert offer.stock_quantity == 1

    events_after = list_order_events(
        db_session,
        order_id=order.id,
    )

    assert len(events_after) == len(events)


def test_paid_order_is_not_expired_or_released(
    db_session: Session,
) -> None:
    order, offer = _create_pending_order(db_session)

    transition_order_status(
        db_session,
        order_id=order.id,
        target_status=(OrderStatus.PAID),
    )

    current_time = datetime.now(UTC)

    order.reservation_expires_at = current_time - timedelta(seconds=1)

    db_session.commit()

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=current_time,
    )

    assert expired_count == 0

    db_session.refresh(order)
    db_session.refresh(offer)

    assert order.status == "paid"
    assert offer.stock_quantity == 0


def test_expiry_releases_stock_for_inactive_offer(
    db_session: Session,
) -> None:
    order, offer = _create_pending_order(db_session)

    current_time = datetime.now(UTC)

    order.reservation_expires_at = current_time - timedelta(seconds=1)

    offer.is_active = False

    db_session.commit()

    expired_count = expire_due_pending_orders(
        db_session,
        current_time=current_time,
    )

    assert expired_count == 1

    db_session.refresh(offer)

    assert offer.stock_quantity == 1
