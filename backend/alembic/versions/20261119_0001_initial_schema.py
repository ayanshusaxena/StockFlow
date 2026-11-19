"""Initial StockFlow product, store, inventory, movement, and activity schema.

Revision ID: 20261119_0001
Revises:
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20261119_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_name", "products", ["name"], unique=False)
    op.create_index("ix_products_category", "products", ["category"], unique=False)

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stores"),
    )
    op.create_index("ix_stores_code", "stores", ["code"], unique=True)
    op.create_index("ix_stores_name", "stores", ["name"], unique=True)

    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_balances_quantity_nonnegative"),
        sa.CheckConstraint(
            "reorder_level >= 0", name="ck_inventory_balances_reorder_level_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name="fk_inventory_balances_product_id_products", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name="fk_inventory_balances_store_id_stores", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_balances"),
        sa.UniqueConstraint("product_id", "store_id", name="uq_inventory_product_store"),
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), server_default="", nullable=False),
        sa.Column("seed_key", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(movement_type = 'sale' AND quantity_delta < 0) OR "
            "(movement_type = 'restock' AND quantity_delta > 0) OR "
            "movement_type = 'adjustment'",
            name="ck_stock_movements_movement_delta_matches_type",
        ),
        sa.CheckConstraint(
            "movement_type IN ('sale', 'restock', 'adjustment')",
            name="ck_stock_movements_movement_type_valid",
        ),
        sa.CheckConstraint("quantity_after >= 0", name="ck_stock_movements_quantity_after_nonnegative"),
        sa.CheckConstraint("quantity_before >= 0", name="ck_stock_movements_quantity_before_nonnegative"),
        sa.CheckConstraint("quantity_delta <> 0", name="ck_stock_movements_quantity_delta_nonzero"),
        sa.CheckConstraint(
            "quantity_after = quantity_before + quantity_delta",
            name="ck_stock_movements_movement_quantity_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "store_id"],
            ["inventory_balances.product_id", "inventory_balances.store_id"],
            name="fk_stock_movements_product_store_inventory_balances",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
        sa.UniqueConstraint("seed_key", name="uq_stock_movements_seed_key"),
    )
    op.create_index(
        "ix_stock_movements_product_store_created",
        "stock_movements",
        ["product_id", "store_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "activity_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movement_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("store_name", sa.String(length=160), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("note", sa.String(length=500), server_default="", nullable=False),
        sa.Column("is_batch", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("seed_key", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('sale', 'restock', 'adjustment', 'csv_import')",
            name="ck_activity_history_event_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["movement_id"], ["stock_movements.id"], name="fk_activity_history_movement_id_stock_movements", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name="fk_activity_history_product_id_products", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name="fk_activity_history_store_id_stores", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_activity_history"),
        sa.UniqueConstraint("movement_id", name="uq_activity_history_movement_id"),
        sa.UniqueConstraint("seed_key", name="uq_activity_history_seed_key"),
    )
    op.create_index("ix_activity_history_occurred_at", "activity_history", ["occurred_at"], unique=False)
    op.create_index("ix_activity_history_product_id", "activity_history", ["product_id"], unique=False)
    op.create_index("ix_activity_history_store_id", "activity_history", ["store_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_history_store_id", table_name="activity_history")
    op.drop_index("ix_activity_history_product_id", table_name="activity_history")
    op.drop_index("ix_activity_history_occurred_at", table_name="activity_history")
    op.drop_table("activity_history")
    op.drop_index("ix_stock_movements_product_store_created", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_table("inventory_balances")
    op.drop_index("ix_stores_name", table_name="stores")
    op.drop_index("ix_stores_code", table_name="stores")
    op.drop_table("stores")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
