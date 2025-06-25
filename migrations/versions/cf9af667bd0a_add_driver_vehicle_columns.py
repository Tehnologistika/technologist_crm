"""add driver & vehicle columns

Revision ID: cf9af667bd0a
Revises: c7393cd03d0e
Create Date: 2025-05-05 15:52:19.483752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf9af667bd0a'
down_revision: Union[str, None] = 'c7393cd03d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # добавляем новые текстовые поля для паспорта водителя и номеров ТС
    op.add_column("orders", sa.Column("driver_passport", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("truck_reg", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("trailer_reg", sa.Text(), nullable=True))


def downgrade() -> None:
    # удаляем поля, если откатываем миграцию
    op.drop_column("orders", "trailer_reg")
    op.drop_column("orders", "truck_reg")
    op.drop_column("orders", "driver_passport")
