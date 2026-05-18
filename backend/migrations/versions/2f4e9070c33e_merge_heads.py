"""merge_heads

Revision ID: 2f4e9070c33e
Revises: 51d6a3f9, c3a1f7d08e55
Create Date: 2026-05-18 02:19:26.428023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f4e9070c33e'
down_revision: Union[str, None] = ('51d6a3f9', 'c3a1f7d08e55')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
