from uuid import uuid4

import pytest
from factories.catalog import (
    create_product_offer,
)
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.domain.order_errors import (
    InvalidOrderTransitionError,
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
    transition_order_status,
)

TEST_CREDENTIAL_HASH = hash_password("order-state-machine-test-credential")


def _new_pending_order(
    db: Session,
) -> Order:
    suffix = uuid4().hex

    user = User(
        email=(f"state-machine-{suffix}@example.com"),
        password_hash=(TEST_CREDENTIAL_HASH),
        is_active=True,
    )

    db.add(user)
    db.flush()

    _, offer = create_product_offer(
        db,
        slug=(f"state-machine-{suffix}"),
        price_cents=1200,
        stock_quantity=10,
    )

    db.commit()

    return create_pending_order(
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
        idempotency_key=(f"state-{uuid4().hex}"),
    )


@pytest.mark.parametrize(
    (
        "current_status",
        "target_status",
    ),
    [
        (
            OrderStatus.PENDING,
            OrderStatus.PAID,
        ),
        (
            OrderStatus.PENDING,
            OrderStatus.CANCELLED,
        ),
        (
            OrderStatus.PENDING,
            OrderStatus.EXPIRED,
        ),
        (
            OrderStatus.PAID,
            OrderStatus.REFUNDED,
        ),
    ],
)
def test_allowed_transition_matrix(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> None:
    assert is_order_transition_allowed(
        current_status,
        target_status,
    )


@pytest.mark.parametrize(
    (
        "current_status",
        "target_status",
    ),
    [
        (
            OrderStatus.PENDING,
            OrderStatus.PENDING,
        ),
        (
            OrderStatus.PAID,
            OrderStatus.PENDING,
        ),
        (
            OrderStatus.CANCELLED,
            OrderStatus.PAID,
        ),
        (
            OrderStatus.EXPIRED,
            OrderStatus.PAID,
        ),
        (
            OrderStatus.REFUNDED,
            OrderStatus.PENDING,
        ),
    ],
)
def test_invalid_transition_matrix(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> None:
    assert not is_order_transition_allowed(
        current_status,
        target_status,
    )


def test_transition_persists_status_and_audit_event(
    db_session: Session,
) -> None:
    order = _new_pending_order(db_session)

    transitioned = transition_order_status(
        db_session,
        order_id=order.id,
        target_status=(OrderStatus.EXPIRED),
    )

    assert transitioned.status == OrderStatus.EXPIRED

    events = list_order_events(
        db_session,
        order_id=order.id,
    )

    assert len(events) == 3

    event = events[-1]

    assert event.event_type == OrderEventType.ORDER_STATUS_CHANGED
    assert event.actor_type == OrderActorType.SYSTEM
    assert event.actor_id is None
    assert event.source == OrderEventSource.ORDER_SERVICE
    assert event.event_data == {
        "from_status": "pending",
        "to_status": "expired",
    }


def test_invalid_transition_rolls_back_without_event(
    db_session: Session,
) -> None:
    order = _new_pending_order(db_session)
    order_id = order.id

    transition_order_status(
        db_session,
        order_id=order_id,
        target_status=(OrderStatus.EXPIRED),
    )

    events_before = list_order_events(
        db_session,
        order_id=order_id,
    )

    with pytest.raises(InvalidOrderTransitionError) as error:
        transition_order_status(
            db_session,
            order_id=order_id,
            target_status=(OrderStatus.PAID),
        )

    assert error.value.current_status == "expired"
    assert error.value.target_status == "paid"

    stored = db_session.get(
        Order,
        order_id,
    )

    assert stored is not None
    assert stored.status == "expired"

    events_after = list_order_events(
        db_session,
        order_id=order_id,
    )

    assert len(events_after) == len(events_before)


def test_paid_order_can_transition_to_refunded(
    db_session: Session,
) -> None:
    order = _new_pending_order(db_session)

    transition_order_status(
        db_session,
        order_id=order.id,
        target_status=(OrderStatus.PAID),
    )

    refunded = transition_order_status(
        db_session,
        order_id=order.id,
        target_status=(OrderStatus.REFUNDED),
    )

    assert refunded.status == "refunded"

    events = list_order_events(
        db_session,
        order_id=order.id,
    )

    assert [event.event_data for event in events[-2:]] == [
        {
            "from_status": "pending",
            "to_status": "paid",
        },
        {
            "from_status": "paid",
            "to_status": "refunded",
        },
    ]
