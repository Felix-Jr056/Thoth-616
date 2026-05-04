from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SourcesSchema(BaseModel):
    interviews: list[str]
    materials: list[str]


class KnowledgeSynthesizeRequest(BaseModel):
    interview_ids: list[str]
    material_ids: list[str]
    topic: str


class KnowledgeSynthesizeResponse(BaseModel):
    entry_id: str
    sme_id: str
    topic: str
    status: str
    content: str
    sources: SourcesSchema
    created_at: datetime
    usage: Optional[dict] = None


class KnowledgeUpdate(BaseModel):
    content: str


class KnowledgeReject(BaseModel):
    reason: Optional[str] = None


class KnowledgeRead(BaseModel):
    entry_id: str
    sme_id: str
    topic: str
    status: str
    content: str
    sources: SourcesSchema
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeApproveResponse(BaseModel):
    entry_id: str
    status: str
    approved_at: datetime


class KnowledgeAdminApproveResponse(BaseModel):
    entry_id: str
    status: str
    admin_approved_at: datetime


class KnowledgeRejectResponse(BaseModel):
    entry_id: str
    status: str
    rejected_at: datetime


class KnowledgeListResponse(BaseModel):
    entries: list[KnowledgeRead]
