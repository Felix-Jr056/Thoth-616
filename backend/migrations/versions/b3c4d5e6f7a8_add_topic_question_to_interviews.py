"""add current_topic_question to interviews

Revision ID: b3c4d5e6f7a8
Revises: 3f7a1d2e, 51d6a3f9
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = ('3f7a1d2e', '51d6a3f9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interviews',
        sa.Column('current_topic_question', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('interviews', 'current_topic_question')
