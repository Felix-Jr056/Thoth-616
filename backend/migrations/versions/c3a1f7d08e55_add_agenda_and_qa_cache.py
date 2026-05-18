"""add agenda fields and qa_cache table

Revision ID: c3a1f7d08e55
Revises: 8c96f40b962e
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

revision: str = 'c3a1f7d08e55'
down_revision: Union[str, None] = '8c96f40b962e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- interviews: agenda and topic-index tracking --
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

    # -- qa_cache --
    op.create_table(
        'qa_cache',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column(
            'question_embedding',
            pgvector.sqlalchemy.vector.VECTOR(dim=1024),
            nullable=False,
        ),
        sa.Column(
            'source_entry_ids',
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default='{}',
        ),
        sa.Column(
            'session_id',
            sa.String(),
            sa.ForeignKey('sessions.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.Column('last_hit_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        'ix_qa_cache_question_embedding',
        'qa_cache',
        ['question_embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100},
        postgresql_ops={'question_embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('ix_qa_cache_question_embedding', table_name='qa_cache')
    op.drop_table('qa_cache')
    op.drop_column('interviews', 'current_topic_index')
    op.drop_column('interviews', 'agenda_json')
