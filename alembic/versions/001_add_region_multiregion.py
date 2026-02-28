"""Add region column to training_runs and create price_records table.

Revision ID: 001_add_region_multiregion
Revises: 
Create Date: 2026-02-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_add_region_multiregion"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add region column to training_runs, default existing rows to 'us'
    with op.batch_alter_table("training_runs") as batch_op:
        batch_op.add_column(
            sa.Column("region", sa.String(16), nullable=False, server_default="us")
        )
        batch_op.create_index("ix_training_runs_region", ["region"])

    # Create price_records table
    op.create_table(
        "price_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(32), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, index=True),
        sa.Column("region", sa.String(16), nullable=False, index=True),
        sa.Column("price_in_grams", sa.Float, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("price_records")
    with op.batch_alter_table("training_runs") as batch_op:
        batch_op.drop_index("ix_training_runs_region")
        batch_op.drop_column("region")
