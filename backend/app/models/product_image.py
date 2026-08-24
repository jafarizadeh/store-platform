from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(Base):
    __tablename__ = "product_images"

    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="ck_product_images_position_nonnegative",
        ),
        UniqueConstraint(
            "product_id",
            "position",
            name="uq_product_images_product_position",
        ),
        UniqueConstraint(
            "product_id",
            "image_path",
            name="uq_product_images_product_path",
        ),
        Index(
            "uq_product_images_one_primary_per_product",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary IS TRUE"),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="images",
    )
