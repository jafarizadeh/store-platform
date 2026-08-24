"""enforce one unresolved payment attempt

Revision ID: 791a543f3da9
Revises: 545a2e221a76
"""

import sqlalchemy as sa
from alembic import op

revision = "791a543f3da9"
down_revision = "545a2e221a76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_payment_attempts_one_unresolved_per_payment",
        "payment_attempts",
        ["payment_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('created', 'pending')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_payment_attempts_one_unresolved_per_payment",
        table_name="payment_attempts",
    )
