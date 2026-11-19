"""Persist idempotency keys for stock movement writes.

Revision ID: 20261119_0003
Revises: 20261119_0002
"""

from alembic import op
import sqlalchemy as sa


revision = "20261119_0003"
down_revision = "20261119_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("movement_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["movement_id"], ["stock_movements.id"], ondelete="CASCADE",
            name="fk_idempotency_records_movement_id_stock_movements",
        ),
        sa.PrimaryKeyConstraint("key", name="pk_idempotency_records"),
        sa.UniqueConstraint("movement_id", name="uq_idempotency_records_movement_id"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
