"""add expired order status

Revision ID: 7ba5bb587d29
Revises: da5d76866a45
"""

from alembic import op

revision = "7ba5bb587d29"
down_revision = "da5d76866a45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_orders_valid_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_valid_status",
        "orders",
        ("status IN ('pending', 'paid', 'cancelled', 'expired', 'refunded')"),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_orders_valid_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_valid_status",
        "orders",
        ("status IN ('pending', 'paid', 'cancelled', 'refunded')"),
    )
