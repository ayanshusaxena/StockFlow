"""Persist idempotency results for inventory CSV commits.

Revision ID: 20261119_0004
Revises: 20261119_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20261119_0004"
down_revision = "20261119_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key", name="pk_import_batches"),
    )


def downgrade() -> None:
    op.drop_table("import_batches")
