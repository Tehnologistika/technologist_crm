"""add carrier_requisites

Revision ID: c7393cd03d0e
Revises: d9ced54c84b6
Create Date: 2025-05-05 13:29:24.817700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7393cd03d0e'
down_revision: Union[str, None] = 'd9ced54c84b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # добавляем колонку carrier_requisites (TEXT, допускаем NULL)
    op.add_column(
        "orders",
        sa.Column("carrier_requisites", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # откатываем изменение
    op.drop_column("orders", "carrier_requisites")
