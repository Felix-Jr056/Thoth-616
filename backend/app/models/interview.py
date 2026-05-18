from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, func, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String, primary_key=True)
    sme_id = Column(String, ForeignKey("smes.id", ondelete="CASCADE"), nullable=False)
    topic = Column(Text, nullable=False)
    status = Column(String, CheckConstraint("status IN ('in_progress', 'completed')"), nullable=False)
    requested_by = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    agenda_json = Column(
        JSONB,
        nullable=False,
        server_default='[]',
        comment="Ordered list of topic strings for this interview session",
    )
    current_topic_index = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment="Index into agenda_json indicating the topic currently being captured",
    )

    sme = relationship("SME", back_populates="interviews")
    turns = relationship("InterviewTurn", back_populates="interview", cascade="all, delete", order_by="InterviewTurn.turn_number")
    topic_summaries = relationship("InterviewTopicSummary", back_populates="interview", cascade="all, delete")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id = Column(String, primary_key=True)
    interview_id = Column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    sme_response = Column(Text, nullable=False)
    agent_follow_up = Column(Text, nullable=True)
    refined_summary = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("interview_id", "turn_number"),)

    interview = relationship("Interview", back_populates="turns")


class InterviewTopicSummary(Base):
    __tablename__ = "interview_topic_summaries"

    id = Column(String, primary_key=True)
    interview_id = Column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    topic_index = Column(Integer, nullable=False)
    topic_question = Column(Text, nullable=False)
    refined_content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("interview_id", "topic_index"),)

    interview = relationship("Interview", back_populates="topic_summaries")
