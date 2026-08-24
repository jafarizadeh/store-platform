from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product_offer import ProductOffer


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled', 'expired', 'refunded')",
            name="ck_orders_valid_status",
        ),
        CheckConstraint(
            "total_cents >= 0",
            name="ck_orders_total_nonnegative",
        ),
        UniqueConstraint(
            "order_number",
            name="uq_orders_order_number",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_orders_user_id_idempotency_key",
        ),
        Index(
            "ix_orders_pending_reservation_expiry",
            "reservation_expires_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_number: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    request_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    reservation_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        server_default="EUR",
    )

    total_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    events: Mapped[list[OrderEvent]] = relationship(
        back_populates="order",
        passive_deletes=True,
        order_by="OrderEvent.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name=("ck_order_items_quantity_positive"),
        ),
        CheckConstraint(
            "unit_price_cents >= 0",
            name=("ck_order_items_price_nonnegative"),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    offer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "product_offers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    offer_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    fulfillment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    unit_price_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    order: Mapped[Order] = relationship(
        back_populates="items",
    )

    offer: Mapped[ProductOffer] = relationship()


class OrderEvent(Base):
    __tablename__ = "order_events"

    __table_args__ = (
        Index(
            "ix_order_events_order_id_id",
            "order_id",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    actor_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    actor_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_data: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped[Order] = relationship(
        back_populates="events",
    )
