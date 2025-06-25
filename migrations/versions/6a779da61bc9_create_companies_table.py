"""create companies table

Revision ID: 6a779da61bc9
Revises: e3ea81245af4
Create Date: 2025-05-16 21:18:48.440765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a779da61bc9'
down_revision: Union[str, None] = 'e3ea81245af4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
