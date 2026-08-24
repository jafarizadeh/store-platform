from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import OrderEvent


def append_order_event(
    db: Session,
    *,
    order_id: UUID,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    source: str,
    event_data: (dict[str, object] | None) = None,
) -> OrderEvent:
    event = OrderEvent(
        order_id=order_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        event_data=event_data or {},
    )

    db.add(event)
    db.flush()

    return event


def list_order_events(
    db: Session,
    *,
    order_id: UUID,
) -> list[OrderEvent]:
    statement = (
        select(OrderEvent)
        .where(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.id.asc())
    )

    return list(db.scalars(statement).all())
