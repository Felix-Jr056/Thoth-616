from pydantic import BaseModel


class SMEProfile(BaseModel):
    id: str
    name: str
    role: str
    department: str
    specialization: str
    responsible_products: list[str]
    sub_expertise: list[str]
    recorded_topics: list[str]


class AdminInitiateInterviewRequest(BaseModel):
    sme_id: str
    topic: str
    requested_by_admin: str
    note: str = ""
