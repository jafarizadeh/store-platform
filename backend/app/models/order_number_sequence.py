from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class OrderDailySequence(Base):
    __tablename__ = "order_daily_sequences"

    __table_args__ = (
        CheckConstraint(
            "last_value >= 1",
            name=("ck_order_daily_sequences_last_value_positive"),
        ),
    )

    order_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )

    last_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
