from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product_offer import ProductOffer

if TYPE_CHECKING:
    from app.models.product_image import ProductImage


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            """
            product_type IN (
                'component',
                'kit',
                'project',
                'solution',
                'service'
            )
            """,
            name="ck_products_product_type",
        ),
        CheckConstraint(
            """
            difficulty_level IS NULL
            OR (
                difficulty_level >= 1
                AND difficulty_level <= 10
            )
            """,
            name="ck_products_difficulty_level",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    product_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="component",
        server_default="component",
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="Other",
        server_default="Other",
        index=True,
    )

    difficulty_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
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

    offers: Mapped[list[ProductOffer]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductOffer.position, ProductOffer.id",
    )

    images: Mapped[list[ProductImage]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImage.position",
    )
