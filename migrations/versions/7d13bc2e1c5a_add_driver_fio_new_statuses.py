"""add driver_fio + new statuses

Revision ID: 7d13bc2e1c5a
Revises: 
Create Date: 2025-05-03 20:28:31.255898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d13bc2e1c5a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply: add driver_fio column, new default for status, map old values."""
    # 1) add the new nullable column
    op.add_column(
        "orders",
        sa.Column("driver_fio", sa.String(), nullable=True),
    )

    # 2) change default value of status → 'confirmed'
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(),
        server_default="confirmed",
    )

    # 3) update existing rows to match new terminology
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE orders SET status='confirmed' WHERE status='new'"))
    conn.execute(sa.text("UPDATE orders SET status='done' WHERE status='closed'"))


def downgrade() -> None:
    """Revert: map status values back, restore default, drop driver_fio."""
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE orders SET status='closed' WHERE status='done'"))
    conn.execute(sa.text("UPDATE orders SET status='new' WHERE status='confirmed'"))

    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(),
        server_default="new",
    )

    op.drop_column("orders", "driver_fio")
