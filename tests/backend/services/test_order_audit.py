import re
from uuid import UUID, uuid4

from factories.catalog import (
    create_product_offer,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth_security import (
    hash_password,
)
from app.domain.order_event import (
    OrderActorType,
    OrderEventSource,
    OrderEventType,
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
)

ORDER_NUMBER_PATTERN = re.compile(r"^BN-\d{6}-\d{4}$")

TEST_CREDENTIAL_HASH = hash_password("order-audit-test-credential")


def _create_user(
    db: Session,
    *,
    email: str,
) -> UUID:
    user = User(
        email=email,
        password_hash=(TEST_CREDENTIAL_HASH),
    )

    db.add(user)
    db.flush()

    user_id = user.id

    db.commit()

    return user_id


def _create_test_order(
    db: Session,
    *,
    user_id: UUID,
    slug: str,
    idempotency_key: str,
):
    _, offer = create_product_offer(
        db,
        slug=slug,
        price_cents=1250,
        stock_quantity=10,
    )

    db.commit()

    order = create_pending_order(
        db,
        OrderCreate(
            items=[
                OrderItemCreate(
                    offer_id=offer.id,
                    quantity=2,
                )
            ]
        ),
        user_id=user_id,
        idempotency_key=(idempotency_key),
    )

    return order, offer


def test_new_order_gets_public_order_number(
    db_session: Session,
) -> None:
    user_id = _create_user(
        db_session,
        email=(f"order-number-{uuid4().hex}@example.com"),
    )

    order, _ = _create_test_order(
        db_session,
        user_id=user_id,
        slug=(f"order-number-{uuid4().hex}"),
        idempotency_key=(f"audit-{uuid4().hex}"),
    )

    assert ORDER_NUMBER_PATTERN.fullmatch(order.order_number)

    database_date = db_session.scalar(
        select(
            func.to_char(
                func.current_date(),
                "YYMMDD",
            )
        )
    )

    assert database_date is not None

    assert order.order_number.startswith(f"BN-{database_date}-")


def test_order_numbers_are_unique(
    db_session: Session,
) -> None:
    user_id = _create_user(
        db_session,
        email=(f"order-number-unique-{uuid4().hex}@example.com"),
    )

    first, _ = _create_test_order(
        db_session,
        user_id=user_id,
        slug=(f"order-number-first-{uuid4().hex}"),
        idempotency_key=(f"audit-first-{uuid4().hex}"),
    )

    second, _ = _create_test_order(
        db_session,
        user_id=user_id,
        slug=(f"order-number-second-{uuid4().hex}"),
        idempotency_key=(f"audit-second-{uuid4().hex}"),
    )

    assert first.order_number != second.order_number


def test_order_creation_records_initial_audit_events(
    db_session: Session,
) -> None:
    user_id = _create_user(
        db_session,
        email=(f"order-events-{uuid4().hex}@example.com"),
    )

    order, offer = _create_test_order(
        db_session,
        user_id=user_id,
        slug=(f"order-events-{uuid4().hex}"),
        idempotency_key=(f"audit-events-{uuid4().hex}"),
    )

    events = list_order_events(
        db_session,
        order_id=order.id,
    )

    assert [event.event_type for event in events] == [
        OrderEventType.ORDER_CREATED,
        OrderEventType.INVENTORY_RESERVED,
    ]

    created_event = events[0]

    assert created_event.actor_type == OrderActorType.CUSTOMER
    assert created_event.actor_id == str(user_id)
    assert created_event.source == OrderEventSource.CHECKOUT
    assert created_event.event_data == {
        "status": "pending",
        "currency": "EUR",
        "total_cents": 2500,
    }

    inventory_event = events[1]

    assert inventory_event.actor_type == OrderActorType.SYSTEM
    assert inventory_event.actor_id is None
    assert inventory_event.source == OrderEventSource.ORDER_SERVICE
    assert inventory_event.event_data == {
        "items": [
            {
                "offer_id": offer.id,
                "quantity": 2,
            }
        ]
    }


def test_idempotent_replay_keeps_number_and_events(
    db_session: Session,
) -> None:
    user_id = _create_user(
        db_session,
        email=(f"order-audit-replay-{uuid4().hex}@example.com"),
    )

    _, offer = create_product_offer(
        db_session,
        slug=(f"order-audit-replay-{uuid4().hex}"),
        price_cents=900,
        stock_quantity=5,
    )

    db_session.commit()

    request = OrderCreate(
        items=[
            OrderItemCreate(
                offer_id=offer.id,
                quantity=1,
            )
        ]
    )

    key = f"audit-replay-{uuid4().hex}"

    first = create_pending_order(
        db_session,
        request,
        user_id=user_id,
        idempotency_key=key,
    )

    first_number = first.order_number

    second = create_pending_order(
        db_session,
        request,
        user_id=user_id,
        idempotency_key=key,
    )

    events = list_order_events(
        db_session,
        order_id=first.id,
    )

    db_session.refresh(offer)

    assert second.id == first.id
    assert second.order_number == first_number
    assert len(events) == 2
    assert offer.stock_quantity == 4
