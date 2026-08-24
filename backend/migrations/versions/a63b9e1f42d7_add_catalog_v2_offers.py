"""add catalog v2 offers

Revision ID: a63b9e1f42d7
Revises: c79eb3c9c11b
Create Date: 2026-08-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a63b9e1f42d7"
down_revision: str | Sequence[str] | None = "c79eb3c9c11b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Product becomes catalog/content metadata rather than a purchasable
    # inventory row.
    # ------------------------------------------------------------------
    op.add_column(
        "products",
        sa.Column(
            "product_type",
            sa.String(length=20),
            server_default="component",
            nullable=False,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "difficulty_level",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_products_product_type",
        "products",
        """
        product_type IN (
            'component',
            'kit',
            'project',
            'solution',
            'service'
        )
        """,
    )

    op.create_check_constraint(
        "ck_products_difficulty_level",
        "products",
        """
        difficulty_level IS NULL
        OR (
            difficulty_level >= 1
            AND difficulty_level <= 10
        )
        """,
    )

    op.create_index(
        "ix_products_product_type",
        "products",
        ["product_type"],
        unique=False,
    )

    op.create_index(
        "ix_products_is_active",
        "products",
        ["is_active"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Purchasable offers / SKUs.
    # ------------------------------------------------------------------
    op.create_table(
        "product_offers",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sku",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "pricing_type",
            sa.String(length=20),
            server_default="fixed",
            nullable=False,
        ),
        sa.Column(
            "fulfillment_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "price_cents",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=True,
        ),
        sa.Column(
            "track_inventory",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "stock_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            server_default="0",
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
            "pricing_type IN ('fixed', 'quote')",
            name="ck_product_offers_pricing_type",
        ),
        sa.CheckConstraint(
            "fulfillment_type IN ('physical', 'digital', 'service')",
            name="ck_product_offers_fulfillment_type",
        ),
        sa.CheckConstraint(
            "price_cents IS NULL OR price_cents >= 0",
            name="ck_product_offers_price_nonnegative",
        ),
        sa.CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_offers_stock_nonnegative",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_product_offers_position_nonnegative",
        ),
        sa.CheckConstraint(
            """
            (
                pricing_type = 'fixed'
                AND price_cents IS NOT NULL
                AND currency IS NOT NULL
            )
            OR
            (
                pricing_type = 'quote'
                AND price_cents IS NULL
            )
            """,
            name="ck_product_offers_pricing_fields",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sku",
            name="uq_product_offers_sku",
        ),
    )

    op.create_index(
        "ix_product_offers_product_id",
        "product_offers",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        "ix_product_offers_is_active",
        "product_offers",
        ["is_active"],
        unique=False,
    )

    # Every legacy Product represented one physical purchasable item.
    # Convert each one to a default Offer before removing legacy fields.
    op.execute(
        sa.text(
            """
            INSERT INTO product_offers (
                product_id,
                sku,
                name,
                pricing_type,
                fulfillment_type,
                price_cents,
                currency,
                track_inventory,
                stock_quantity,
                is_active,
                position
            )
            SELECT
                id,
                'legacy-' || id::text,
                'Standard',
                'fixed',
                'physical',
                price_cents,
                currency,
                true,
                stock_quantity,
                is_active,
                0
            FROM products
            ORDER BY id
            """
        )
    )

    # ------------------------------------------------------------------
    # Existing order items move from Product -> ProductOffer.
    # Add nullable columns first so legacy rows can be backfilled.
    # ------------------------------------------------------------------
    op.add_column(
        "order_items",
        sa.Column(
            "offer_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "order_items",
        sa.Column(
            "offer_name",
            sa.String(length=160),
            nullable=True,
        ),
    )

    op.add_column(
        "order_items",
        sa.Column(
            "sku",
            sa.String(length=120),
            nullable=True,
        ),
    )

    op.add_column(
        "order_items",
        sa.Column(
            "fulfillment_type",
            sa.String(length=20),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE order_items AS oi
            SET
                offer_id = po.id,
                offer_name = po.name,
                sku = po.sku,
                fulfillment_type = po.fulfillment_type
            FROM product_offers AS po
            WHERE po.product_id = oi.product_id
            """
        )
    )

    op.alter_column(
        "order_items",
        "offer_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "order_items",
        "offer_name",
        existing_type=sa.String(length=160),
        nullable=False,
    )

    op.alter_column(
        "order_items",
        "sku",
        existing_type=sa.String(length=120),
        nullable=False,
    )

    op.alter_column(
        "order_items",
        "fulfillment_type",
        existing_type=sa.String(length=20),
        nullable=False,
    )

    op.create_foreign_key(
        "order_items_offer_id_fkey",
        "order_items",
        "product_offers",
        ["offer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_order_items_offer_id",
        "order_items",
        ["offer_id"],
        unique=False,
    )

    # Remove old Product relationship only after all legacy rows have
    # successfully moved to an Offer.
    op.drop_constraint(
        "order_items_product_id_fkey",
        "order_items",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_order_items_product_id",
        table_name="order_items",
    )

    op.drop_column(
        "order_items",
        "product_id",
    )

    # Price and inventory now belong exclusively to ProductOffer.
    op.drop_constraint(
        "ck_products_price_nonnegative",
        "products",
        type_="check",
    )

    op.drop_constraint(
        "ck_products_stock_nonnegative",
        "products",
        type_="check",
    )

    op.drop_column(
        "products",
        "price_cents",
    )

    op.drop_column(
        "products",
        "currency",
    )

    op.drop_column(
        "products",
        "stock_quantity",
    )


def downgrade() -> None:
    # Recreate the legacy Product pricing/inventory representation.
    op.add_column(
        "products",
        sa.Column(
            "price_cents",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="EUR",
            nullable=False,
        ),
    )

    op.add_column(
        "products",
        sa.Column(
            "stock_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    # Downgrade is necessarily lossy when a Product has multiple offers.
    # Pick the preferred fixed-price offer deterministically.
    op.execute(
        sa.text(
            """
            UPDATE products AS p
            SET
                price_cents = chosen.price_cents,
                currency = chosen.currency,
                stock_quantity = CASE
                    WHEN chosen.track_inventory
                    THEN chosen.stock_quantity
                    ELSE 0
                END
            FROM (
                SELECT DISTINCT ON (product_id)
                    product_id,
                    price_cents,
                    currency,
                    track_inventory,
                    stock_quantity
                FROM product_offers
                WHERE
                    pricing_type = 'fixed'
                    AND price_cents IS NOT NULL
                    AND currency IS NOT NULL
                ORDER BY
                    product_id,
                    is_active DESC,
                    position,
                    id
            ) AS chosen
            WHERE chosen.product_id = p.id
            """
        )
    )

    op.alter_column(
        "products",
        "price_cents",
        server_default=None,
    )

    op.create_check_constraint(
        "ck_products_price_nonnegative",
        "products",
        "price_cents >= 0",
    )

    op.create_check_constraint(
        "ck_products_stock_nonnegative",
        "products",
        "stock_quantity >= 0",
    )

    # Restore legacy order_items.product_id.
    op.add_column(
        "order_items",
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE order_items AS oi
            SET product_id = po.product_id
            FROM product_offers AS po
            WHERE po.id = oi.offer_id
            """
        )
    )

    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "order_items_product_id_fkey",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_order_items_product_id",
        "order_items",
        ["product_id"],
        unique=False,
    )

    op.drop_constraint(
        "order_items_offer_id_fkey",
        "order_items",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_order_items_offer_id",
        table_name="order_items",
    )

    op.drop_column(
        "order_items",
        "fulfillment_type",
    )

    op.drop_column(
        "order_items",
        "sku",
    )

    op.drop_column(
        "order_items",
        "offer_name",
    )

    op.drop_column(
        "order_items",
        "offer_id",
    )

    op.drop_index(
        "ix_product_offers_is_active",
        table_name="product_offers",
    )

    op.drop_index(
        "ix_product_offers_product_id",
        table_name="product_offers",
    )

    op.drop_table(
        "product_offers",
    )

    op.drop_index(
        "ix_products_is_active",
        table_name="products",
    )

    op.drop_index(
        "ix_products_product_type",
        table_name="products",
    )

    op.drop_constraint(
        "ck_products_difficulty_level",
        "products",
        type_="check",
    )

    op.drop_constraint(
        "ck_products_product_type",
        "products",
        type_="check",
    )

    op.drop_column(
        "products",
        "difficulty_level",
    )

    op.drop_column(
        "products",
        "product_type",
    )
