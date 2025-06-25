"""add requisites + cars json

Revision ID: d9ced54c84b6
Revises: 7d13bc2e1c5a
Create Date: 2025-05-05 12:41:20.034531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ced54c84b6'
down_revision: Union[str, None] = '7d13bc2e1c5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add text columns for requisites
    op.add_column('orders', sa.Column('cust_requisites', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('carrier_requisites', sa.Text(), nullable=True))

    # JSON columns for cars / loads / unloads (PostgreSQL JSONB)
    op.add_column('orders', sa.Column('cars', sa.JSON(), nullable=True))
    op.add_column('orders', sa.Column('loads', sa.JSON(), nullable=True))
    op.add_column('orders', sa.Column('unloads', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'unloads')
    op.drop_column('orders', 'loads')
    op.drop_column('orders', 'cars')
    op.drop_column('orders', 'carrier_requisites')
    op.drop_column('orders', 'cust_requisites')
