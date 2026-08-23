"""add product images

Revision ID: f28c4d7a91b3
Revises: a63b9e1f42d7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f28c4d7a91b3"
down_revision: str | Sequence[str] | None = "a63b9e1f42d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_images",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "image_path",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "alt_text",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name=("ck_product_images_position_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "image_path",
            name=("uq_product_images_product_path"),
        ),
        sa.UniqueConstraint(
            "product_id",
            "position",
            name=("uq_product_images_product_position"),
        ),
    )

    op.create_index(
        "uq_product_images_one_primary_per_product",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )

    # Preserve every legacy Product.image_path
    # as the first ProductImage.
    op.execute(
        sa.text(
            """
            INSERT INTO product_images (
                product_id,
                image_path,
                alt_text,
                position,
                is_primary
            )
            SELECT
                id,
                image_path,
                name,
                0,
                TRUE
            FROM products
            WHERE image_path IS NOT NULL
              AND image_path <> ''
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "uq_product_images_one_primary_per_product",
        table_name="product_images",
    )

    op.drop_table("product_images")
