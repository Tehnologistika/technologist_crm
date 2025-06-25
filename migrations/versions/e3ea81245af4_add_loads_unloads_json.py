"""add loads & unloads json

Revision ID: e3ea81245af4
Revises: cf9af667bd0a
Create Date: 2025-05-05 16:23:25.446159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3ea81245af4'
down_revision: Union[str, None] = 'cf9af667bd0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # добавляем JSONB‑поля для точек погрузки и выгрузки
    op.add_column(
        "orders",
        sa.Column(
            "loads",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Список точек погрузки [{place, date}]",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "unloads",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Список точек выгрузки [{place, date}]",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "unloads")
    op.drop_column("orders", "loads")
