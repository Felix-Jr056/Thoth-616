from sqlalchemy import Column, String, ARRAY, TIMESTAMP, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db import Base

class SME(Base):
    __tablename__ = "smes"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    specialization = Column(String, nullable=False)
    sub_areas = Column(ARRAY(String), nullable=False)
    contact_email = Column(String, nullable=False)
    role = Column(String, nullable=True)
    department = Column(String, nullable=True)
    responsible_products = Column(ARRAY(String), nullable=True)
    sub_expertise = Column(ARRAY(String), nullable=True)
    embedding = Column(Vector(1024), nullable=True)
    embedding_status = Column(
        String,
        nullable=False,
        server_default='pending',
        comment="Tracks embedding lifecycle: pending | done | failed",
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    interviews = relationship("Interview", back_populates="sme", cascade="all, delete")
    materials = relationship("Material", back_populates="sme", cascade="all, delete")
    knowledge_entries = relationship("KnowledgeEntry", back_populates="sme", cascade="all, delete")
