"""add daily order numbers and fulfillment statuses

Revision ID: 265fb045c9f3
Revises: 17ca81329820
Create Date: 2026-09-04 14:41:36.506422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '265fb045c9f3'
down_revision: Union[str, Sequence[str], None] = '17ca81329820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "order_daily_sequences",
        sa.Column(
            "order_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "last_value",
            sa.Integer(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_value >= 1",
            name=(
                "ck_order_daily_sequences_"
                "last_value_positive"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "order_date",
        ),
    )

    op.drop_constraint(
        "ck_orders_valid_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_valid_status",
        "orders",
        (
            "status IN ("
            "'pending', "
            "'paid', "
            "'processing', "
            "'shipped', "
            "'delivered', "
            "'cancelled', "
            "'expired', "
            "'refunded'"
            ")"
        ),
    )


    op.execute(
        sa.text(
            "DROP SEQUENCE IF EXISTS order_number_seq"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "CREATE SEQUENCE IF NOT EXISTS order_number_seq"
        )
    )

    op.drop_constraint(
        "ck_orders_valid_status",
        "orders",
        type_="check",
    )

    op.create_check_constraint(
        "ck_orders_valid_status",
        "orders",
        (
            "status IN ("
            "'pending', "
            "'paid', "
            "'cancelled', "
            "'expired', "
            "'refunded'"
            ")"
        ),
    )

    op.drop_table(
        "order_daily_sequences",
    )
