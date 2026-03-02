"""Add WhatsApp alert columns to price_alerts.

Revision ID: 002_whatsapp_price_alerts
Revises: 001_add_region_multiregion
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_whatsapp_price_alerts"
down_revision = "001_add_region_multiregion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    direction_enum = sa.Enum("above", "below", name="price_alert_direction", native_enum=False)
    with op.batch_alter_table("price_alerts") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=128), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("target_price", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("direction", direction_enum, nullable=True))
        batch_op.add_column(sa.Column("whatsapp_number", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("triggered_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_price_alerts_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_price_alerts_direction", ["direction"], unique=False)
        batch_op.create_index("ix_price_alerts_is_active", ["is_active"], unique=False)
        batch_op.create_index("ix_price_alerts_is_triggered", ["is_triggered"], unique=False)

    op.execute("UPDATE price_alerts SET user_id = user_sub WHERE user_id = ''")
    op.execute("UPDATE price_alerts SET target_price = threshold WHERE target_price = 0")
    op.execute("UPDATE price_alerts SET direction = alert_type WHERE alert_type IN ('above', 'below') AND direction IS NULL")
    op.execute("UPDATE price_alerts SET is_active = enabled")


def downgrade() -> None:
    with op.batch_alter_table("price_alerts") as batch_op:
        batch_op.drop_index("ix_price_alerts_is_triggered")
        batch_op.drop_index("ix_price_alerts_is_active")
        batch_op.drop_index("ix_price_alerts_direction")
        batch_op.drop_index("ix_price_alerts_user_id")
        batch_op.drop_column("triggered_at")
        batch_op.drop_column("is_triggered")
        batch_op.drop_column("is_active")
        batch_op.drop_column("whatsapp_number")
        batch_op.drop_column("direction")
        batch_op.drop_column("target_price")
        batch_op.drop_column("user_id")
