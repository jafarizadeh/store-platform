"""add payment attempt approval url

Revision ID: 545a2e221a76
Revises: 97215cf9479b
"""

import sqlalchemy as sa
from alembic import op

revision = "545a2e221a76"
down_revision = "97215cf9479b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_attempts",
        sa.Column(
            "approval_url",
            sa.String(length=2000),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "payment_attempts",
        "approval_url",
    )
