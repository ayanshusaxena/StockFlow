from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "store_id"],
            ["inventory_balances.product_id", "inventory_balances.store_id"],
            ondelete="RESTRICT",
            name="fk_stock_movements_product_store_inventory_balances",
        ),
        CheckConstraint("quantity_before >= 0", name="quantity_before_nonnegative"),
        CheckConstraint("quantity_after >= 0", name="quantity_after_nonnegative"),
        CheckConstraint("quantity_delta <> 0", name="quantity_delta_nonzero"),
        CheckConstraint(
            "movement_type IN ('sale', 'restock', 'adjustment')", name="movement_type_valid"
        ),
        CheckConstraint(
            "(movement_type = 'sale' AND quantity_delta < 0) OR "
            "(movement_type = 'restock' AND quantity_delta > 0) OR "
            "movement_type = 'adjustment'",
            name="movement_delta_matches_type",
        ),
        CheckConstraint(
            "quantity_after = quantity_before + quantity_delta", name="movement_quantity_consistent"
        ),
        Index("ix_stock_movements_product_store_created", "product_id", "store_id", "created_at"),
        Index("ix_stock_movements_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(nullable=False)
    store_id: Mapped[int] = mapped_column(nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    seed_key: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
