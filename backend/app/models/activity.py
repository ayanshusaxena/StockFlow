from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActivityHistory(Base):
    __tablename__ = "activity_history"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('sale', 'restock', 'adjustment', 'csv_import')",
            name="event_type_valid",
        ),
        Index("ix_activity_history_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    store_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    seed_key: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
