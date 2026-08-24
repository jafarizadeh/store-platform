from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            name="uq_payments_order_id",
        ),
        CheckConstraint(
            ("status IN ('pending', 'succeeded', 'cancelled', 'refunded')"),
            name="ck_payments_valid_status",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_payments_amount_nonnegative",
        ),
        Index(
            "ix_payments_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
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

    attempts: Mapped[list[PaymentAttempt]] = relationship(
        back_populates="payment",
        passive_deletes=True,
        order_by="PaymentAttempt.created_at",
    )


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    __table_args__ = (
        UniqueConstraint(
            "payment_id",
            "idempotency_key",
            name=("uq_payment_attempts_payment_id_idempotency_key"),
        ),
        UniqueConstraint(
            "provider",
            "provider_reference",
            name=("uq_payment_attempts_provider_reference"),
        ),
        CheckConstraint(
            ("status IN ('created', 'pending', 'succeeded', 'failed', 'cancelled')"),
            name=("ck_payment_attempts_valid_status"),
        ),
        Index(
            "ix_payment_attempts_payment_created",
            "payment_id",
            "created_at",
        ),
        Index(
            "uq_payment_attempts_one_unresolved_per_payment",
            "payment_id",
            unique=True,
            postgresql_where=text("status IN ('created', 'pending')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "payments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="created",
        server_default="created",
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    approval_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
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

    payment: Mapped[Payment] = relationship(
        back_populates="attempts",
    )
