"""add agenda_json and current_topic_index to interviews

Revision ID: 3f7a1d2e
Revises: 8c96f40b962e
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3f7a1d2e'
down_revision: Union[str, None] = '8c96f40b962e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interviews',
        sa.Column(
            'agenda_json',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
    )
    op.add_column(
        'interviews',
        sa.Column(
            'current_topic_index',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )


def downgrade() -> None:
    op.drop_column('interviews', 'current_topic_index')
    op.drop_column('interviews', 'agenda_json')
