from pydantic import BaseModel


class SynthesisRequest(BaseModel):
    interview_id: str
    sme_id: str
    sme_name: str
    specialization: str


class TopicItem(BaseModel):
    title: str
    content: str
    caveats: list[str]
    source_interview_id: str


class SynthesisContent(BaseModel):
    sme_name: str
    specialization: str
    generated_at: str
    topics: list[TopicItem]
    summary: str


class SynthesisResponse(BaseModel):
    entry_id: str
    content: SynthesisContent
    status: str
