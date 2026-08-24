from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductOffer(Base):
    __tablename__ = "product_offers"

    __table_args__ = (
        UniqueConstraint(
            "sku",
            name="uq_product_offers_sku",
        ),
        CheckConstraint(
            "pricing_type IN ('fixed', 'quote')",
            name="ck_product_offers_pricing_type",
        ),
        CheckConstraint(
            "fulfillment_type IN ('physical', 'digital', 'service')",
            name="ck_product_offers_fulfillment_type",
        ),
        CheckConstraint(
            "price_cents IS NULL OR price_cents >= 0",
            name="ck_product_offers_price_nonnegative",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_offers_stock_nonnegative",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_product_offers_position_nonnegative",
        ),
        CheckConstraint(
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
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    sku: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    pricing_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fixed",
        server_default="fixed",
    )

    fulfillment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    price_cents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    track_inventory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    product: Mapped[Product] = relationship(
        back_populates="offers",
    )
