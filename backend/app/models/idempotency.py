from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("movement_id", name="uq_idempotency_records_movement_id"),)

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    movement_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="CASCADE")
    )
