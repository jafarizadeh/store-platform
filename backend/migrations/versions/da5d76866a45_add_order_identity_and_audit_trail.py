"""add order identity and audit trail

Revision ID: da5d76866a45
Revises: 6bf04a07e609
Create Date: 2026-08-24 10:25:43.449784
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "da5d76866a45"
down_revision: str | Sequence[str] | None = "6bf04a07e609"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE SEQUENCE order_number_seq
                AS BIGINT
                START WITH 1
                INCREMENT BY 1
                NO MINVALUE
                NO MAXVALUE
                CACHE 1
            """
        )
    )

    op.create_table(
        "order_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "actor_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_order_events_order_id_id",
        "order_events",
        ["order_id", "id"],
        unique=False,
    )

    # Nullable first: existing orders need a safe
    # backfill before NOT NULL can be enforced.
    op.add_column(
        "orders",
        sa.Column(
            "order_number",
            sa.String(length=24),
            nullable=True,
        ),
    )

    # Backfill is deterministic for legacy rows.
    # The suffix is globally increasing; the year is
    # taken from the original order creation time.
    op.execute(
        sa.text(
            """
            WITH numbered_orders AS (
                SELECT
                    id,
                    created_at,
                    row_number() OVER (
                        ORDER BY
                            created_at ASC,
                            id ASC
                    ) AS sequence_number
                FROM orders
            )
            UPDATE orders AS target
            SET order_number =
                'BY-'
                || to_char(
                    numbered.created_at,
                    'YYYY'
                )
                || '-'
                || lpad(
                    numbered.sequence_number
                        ::text,
                    8,
                    '0'
                )
            FROM numbered_orders AS numbered
            WHERE target.id = numbered.id
            """
        )
    )

    # Continue future allocations after all legacy
    # rows. For an empty table, the first nextval()
    # still returns 1.
    op.execute(
        sa.text(
            """
            SELECT setval(
                'order_number_seq',
                GREATEST(
                    (
                        SELECT count(*)
                        FROM orders
                    ),
                    1
                ),
                (
                    SELECT count(*) > 0
                    FROM orders
                )
            )
            """
        )
    )

    op.alter_column(
        "orders",
        "order_number",
        existing_type=sa.String(length=24),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_orders_order_number",
        "orders",
        ["order_number"],
    )

    # We cannot truthfully reconstruct events that
    # happened before this audit system existed.
    # Instead, create an explicit audit baseline.
    op.execute(
        sa.text(
            """
            INSERT INTO order_events (
                order_id,
                event_type,
                actor_type,
                actor_id,
                source,
                event_data,
                created_at
            )
            SELECT
                id,
                'audit_baseline_created',
                'system',
                NULL,
                'migration',
                jsonb_build_object(
                    'legacy_order',
                    true,
                    'order_number',
                    order_number,
                    'status',
                    status,
                    'original_created_at',
                    created_at
                ),
                now()
            FROM orders
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orders_order_number",
        "orders",
        type_="unique",
    )

    op.drop_column(
        "orders",
        "order_number",
    )

    op.drop_index(
        "ix_order_events_order_id_id",
        table_name="order_events",
    )

    op.drop_table("order_events")

    op.execute(sa.text("DROP SEQUENCE order_number_seq"))
