"""add webhook processing lease

Revision ID: 17ca81329820
Revises: 978c95c2da2a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "17ca81329820"
down_revision: str | None = "978c95c2da2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_webhook_events",
        sa.Column(
            "processing_token",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.add_column(
        "payment_webhook_events",
        sa.Column(
            "processing_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        ("ck_payment_webhook_events_processing_lease_pair"),
        "payment_webhook_events",
        """
        (
            processing_token IS NULL
            AND processing_started_at IS NULL
        )
        OR
        (
            processing_token IS NOT NULL
            AND processing_started_at IS NOT NULL
        )
        """,
    )

    op.create_index(
        ("ix_payment_webhook_events_processing_started_at"),
        "payment_webhook_events",
        ["processing_started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        ("ix_payment_webhook_events_processing_started_at"),
        table_name="payment_webhook_events",
    )

    op.drop_constraint(
        ("ck_payment_webhook_events_processing_lease_pair"),
        "payment_webhook_events",
        type_="check",
    )

    op.drop_column(
        "payment_webhook_events",
        "processing_started_at",
    )

    op.drop_column(
        "payment_webhook_events",
        "processing_token",
    )
