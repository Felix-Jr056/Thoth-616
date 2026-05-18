from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
from app.db import Base


class QACache(Base):
    __tablename__ = "qa_cache"

    id = Column(String, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    question_embedding = Column(Vector(1024), nullable=False)
    source_entry_ids = Column(
        ARRAY(String),
        nullable=False,
        server_default='{}',
        comment="knowledge_entry ids whose content contributed to this answer",
    )
    session_id = Column(String, nullable=True)
    hit_count = Column(Integer, nullable=False, server_default='0')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_hit_at = Column(TIMESTAMP(timezone=True), nullable=True)
