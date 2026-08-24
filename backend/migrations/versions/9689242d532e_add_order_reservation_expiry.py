"""add order reservation expiry

Revision ID: 9689242d532e
Revises: 7ba5bb587d29
"""

import sqlalchemy as sa
from alembic import op

revision = "9689242d532e"
down_revision = "7ba5bb587d29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "reservation_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Existing pending orders receive a
    # deployment-time grace period rather
    # than expiring immediately.
    op.execute(
        """
        UPDATE orders
        SET reservation_expires_at =
            CASE
                WHEN status = 'pending'
                    THEN now()
                        + INTERVAL '15 minutes'
                ELSE created_at
                    + INTERVAL '15 minutes'
            END
        WHERE reservation_expires_at IS NULL
        """
    )

    op.alter_column(
        "orders",
        "reservation_expires_at",
        nullable=False,
    )

    op.create_index(
        "ix_orders_pending_reservation_expiry",
        "orders",
        ["reservation_expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orders_pending_reservation_expiry",
        table_name="orders",
    )

    op.drop_column(
        "orders",
        "reservation_expires_at",
    )
