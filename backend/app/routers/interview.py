from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import interview_repo, interview_service
from app.middleware.auth import verify_token
from app.schemas.interview import (
    CreateInterviewResponse,
    ResumeResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    SupplementRequest,
)
from app.schemas.sme_profile import AdminInitiateInterviewRequest

router = APIRouter(prefix="/interviews", tags=["interviews"], dependencies=[Depends(verify_token)])


# ------------------------------------------------------------------ request schemas

class CreateInterviewRequest(BaseModel):
    sme_id: str
    name: str
    role: str
    department: str
    specialization: str
    responsible_products: list[str]
    sub_expertise: list[str]
    recorded_topics: list[str] = []
    agenda: list[str]


class AgendaRequest(BaseModel):
    sme_profile: dict
    unanswered_questions: list[str]
    uploaded_materials: str = ""


# ------------------------------------------------------------------ static routes first (before path-param routes)

@router.post("/agenda")
async def generate_agenda(body: AgendaRequest):
    agenda = await interview_service.generate_agenda(
        sme_profile=body.sme_profile,
        unanswered_questions=body.unanswered_questions,
        uploaded_materials=body.uploaded_materials,
    )
    return {"agenda": agenda}


@router.post("/admin-initiate")
async def admin_initiate_interview(body: AdminInitiateInterviewRequest):
    interview = await interview_repo.create(
        sme_id=body.sme_id,
        topic=body.topic,
        requested_by=body.requested_by_admin,
        admin_note=body.note,
    )
    interview["status"] = "pending_sme"
    return {
        "interview_id": interview["id"],
        "sme_id": interview["sme_id"],
        "topic": interview["topic"],
        "requested_by": interview["requested_by"],
        "admin_note": interview["admin_note"],
        "status": "pending_sme",
    }


# ------------------------------------------------------------------ collection routes

@router.post("", response_model=CreateInterviewResponse)
async def create_interview(body: CreateInterviewRequest):
    return await interview_service.create_interview(
        sme_id=body.sme_id,
        name=body.name,
        role=body.role,
        department=body.department,
        specialization=body.specialization,
        responsible_products=body.responsible_products,
        sub_expertise=body.sub_expertise,
        recorded_topics=body.recorded_topics,
        agenda=body.agenda,
    )


# ------------------------------------------------------------------ item routes

@router.post("/{interview_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(interview_id: str, body: SubmitAnswerRequest):
    result = await interview_service.submit_answer(
        interview_id=interview_id,
        sme_response=body.sme_response,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Interview {interview_id} not found")
    return result


@router.post("/{interview_id}/supplement", response_model=SubmitAnswerResponse)
async def add_supplement(interview_id: str, body: SupplementRequest):
    try:
        return await interview_service.add_supplement(
            interview_id=interview_id,
            supplement=body.supplement,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{interview_id}/resume", response_model=ResumeResponse)
async def resume_interview(interview_id: str):
    try:
        return await interview_service.resume_interview(interview_id=interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{interview_id}/topics/complete")
async def complete_topic(interview_id: str):
    try:
        return await interview_service.complete_topic(interview_id=interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{interview_id}/topics/next")
async def get_next_topic(interview_id: str):
    try:
        return await interview_service.get_next_topic(interview_id=interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
