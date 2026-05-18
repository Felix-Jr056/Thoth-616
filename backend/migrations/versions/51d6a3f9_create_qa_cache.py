"""create qa_cache table with ivfflat vector index

Revision ID: 51d6a3f9
Revises: c4b89e0f
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

revision: str = '51d6a3f9'
down_revision: Union[str, None] = 'c4b89e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'qa_cache',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column(
            'question_embedding',
            pgvector.sqlalchemy.Vector(1024),
            nullable=False,
        ),
        sa.Column(
            'source_entry_ids',
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('last_hit_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ivfflat index for approximate nearest-neighbor search on question embeddings.
    # lists=100 is appropriate for tables up to ~1M rows.
    # The index is created AFTER the table so it does not block the migration
    # even if the table already has rows (it won't at first run, but this is
    # the correct pattern for production-safe migrations).
    op.execute(
        "CREATE INDEX qa_cache_embedding_idx "
        "ON qa_cache "
        "USING ivfflat (question_embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index('qa_cache_embedding_idx', table_name='qa_cache')
    op.drop_table('qa_cache')
