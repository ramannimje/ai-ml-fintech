"""add region column to training_runs

Revision ID: 20260215_01
Revises:
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260215_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("training_runs", sa.Column("region", sa.String(length=16), nullable=False, server_default="us"))
    op.create_index("ix_training_runs_region", "training_runs", ["region"])


def downgrade() -> None:
    op.drop_index("ix_training_runs_region", table_name="training_runs")
    op.drop_column("training_runs", "region")
