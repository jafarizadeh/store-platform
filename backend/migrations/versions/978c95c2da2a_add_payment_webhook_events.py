"""add payment webhook events

Revision ID: 978c95c2da2a
Revises: 791a543f3da9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "978c95c2da2a"
down_revision: str | None = "791a543f3da9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_events",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "provider_event_id",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "provider_reference",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "payment_attempt_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["payment_attempt_id"],
            ["payment_attempts.id"],
            name=("fk_payment_webhook_events_payment_attempt_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_payment_webhook_events",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name=("uq_payment_webhook_events_provider_event"),
        ),
    )

    op.create_index(
        "ix_payment_webhook_events_received_at",
        "payment_webhook_events",
        ["received_at"],
        unique=False,
    )

    op.create_index(
        "ix_payment_webhook_events_provider_reference",
        "payment_webhook_events",
        [
            "provider",
            "provider_reference",
        ],
        unique=False,
    )

    op.create_index(
        "ix_payment_webhook_events_attempt",
        "payment_webhook_events",
        ["payment_attempt_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_webhook_events_attempt",
        table_name="payment_webhook_events",
    )

    op.drop_index(
        "ix_payment_webhook_events_provider_reference",
        table_name="payment_webhook_events",
    )

    op.drop_index(
        "ix_payment_webhook_events_received_at",
        table_name="payment_webhook_events",
    )

    op.drop_table("payment_webhook_events")
