"""add embedding_status to smes

Revision ID: c4b89e0f
Revises: 3f7a1d2e
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c4b89e0f'
down_revision: Union[str, None] = '3f7a1d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'smes',
        sa.Column(
            'embedding_status',
            sa.String(),
            nullable=False,
            server_default='pending',
        ),
    )


def downgrade() -> None:
    op.drop_column('smes', 'embedding_status')
