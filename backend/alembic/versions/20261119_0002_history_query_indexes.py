"""Add indexes for store filtering and unfiltered movement history.

Revision ID: 20261119_0002
Revises: 20261119_0001
Create Date: 2026-11-19
"""

from alembic import op


revision = "20261119_0002"
down_revision = "20261119_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_inventory_balances_store", "inventory_balances", ["store_id"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_index("ix_inventory_balances_store", table_name="inventory_balances")
