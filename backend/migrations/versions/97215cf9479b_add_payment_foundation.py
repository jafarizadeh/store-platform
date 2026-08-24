"""add payment foundation

Revision ID: 97215cf9479b
Revises: 9689242d532e
"""

import sqlalchemy as sa
from alembic import op

revision = "97215cf9479b"
down_revision = "9689242d532e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "amount_cents",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            ("status IN ('pending', 'succeeded', 'cancelled', 'refunded')"),
            name="ck_payments_valid_status",
        ),
        sa.CheckConstraint(
            "amount_cents >= 0",
            name=("ck_payments_amount_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_id",
            name="uq_payments_order_id",
        ),
    )

    op.create_index(
        "ix_payments_status_created_at",
        "payments",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "payment_attempts",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="created",
            nullable=False,
        ),
        sa.Column(
            "provider_reference",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "failure_code",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            ("status IN ('created', 'pending', 'succeeded', 'failed', 'cancelled')"),
            name=("ck_payment_attempts_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_id",
            "idempotency_key",
            name=("uq_payment_attempts_payment_id_idempotency_key"),
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_reference",
            name=("uq_payment_attempts_provider_reference"),
        ),
    )

    op.create_index(
        "ix_payment_attempts_payment_created",
        "payment_attempts",
        ["payment_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_attempts_payment_created",
        table_name="payment_attempts",
    )

    op.drop_table("payment_attempts")

    op.drop_index(
        "ix_payments_status_created_at",
        table_name="payments",
    )

    op.drop_table("payments")
