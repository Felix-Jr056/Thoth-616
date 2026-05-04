from typing import Optional
from pydantic import BaseModel
from datetime import datetime


# -- A's schemas (benchmark API contract) ------------------------------

class InterviewCreate(BaseModel):
    topic: str

class InterviewTurnCreate(BaseModel):
    sme_response: str

class InterviewTurnRead(BaseModel):
    turn_number: int
    sme_response: str
    agent_follow_up: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}

class InterviewTurnResponse(BaseModel):
    turn_number: int
    sme_response: str
    agent_follow_up: Optional[str]
    timestamp: datetime
    usage: Optional[dict] = None

class InterviewSummary(BaseModel):
    interview_id: str
    topic: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

class InterviewRead(BaseModel):
    interview_id: str
    sme_id: str
    topic: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

class InterviewWithTurns(BaseModel):
    interview_id: str
    sme_id: str
    topic: str
    status: str
    turns: list[InterviewTurnRead]

    model_config = {"from_attributes": True}

class InterviewListResponse(BaseModel):
    interviews: list[InterviewSummary]


# -- C's schemas (interview service) -----------------------------------

class CreateInterviewResponse(BaseModel):
    interview_id: str
    first_question: str
    topic_index: int

class SubmitAnswerRequest(BaseModel):
    sme_response: str

class SubmitAnswerResponse(BaseModel):
    type: str
    question: Optional[str] = None
    topic_index: Optional[int] = None
    turn_number: Optional[int] = None
    interview_id: Optional[str] = None

class SupplementRequest(BaseModel):
    supplement: str

class ResumeResponse(BaseModel):
    topic_index: int
    turn_number: int
    last_question: str
