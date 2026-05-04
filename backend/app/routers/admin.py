from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.db import get_db
from app.middleware.auth import verify_token
from app.models.sme import SME
from app.models.interview import Interview
from app.models.knowledge import KnowledgeEntry
from app.repositories.interview_repository import InterviewRepository

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


# Dashboard KPIs
@router.get("/admin/dashboard/kpis")
async def get_dashboard_kpis(db: AsyncSession = Depends(get_db)):
    sme_count = await db.scalar(select(func.count()).select_from(SME))
    pending_count = await db.scalar(
        select(func.count()).select_from(KnowledgeEntry)
        .where(KnowledgeEntry.status == "sme_approved")
    )
    approved_count = await db.scalar(
        select(func.count()).select_from(KnowledgeEntry)
        .where(KnowledgeEntry.status == "approved")
    )
    return {
        "pendingApprovals": pending_count or 0,
        "smesOnboarded": sme_count or 0,
        "approvedEntries": approved_count or 0,
        "escalatedQuestions": 0,
    }


# SME list with search + stats
@router.get("/admin/smes")
async def list_smes_with_stats(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(SME).order_by(SME.created_at.desc())
    result = await db.execute(query)
    smes = result.scalars().all()

    output = []
    for sme in smes:
        if q:
            q_lower = q.lower()
            if not any([
                q_lower in sme.name.lower(),
                q_lower in sme.specialization.lower(),
                q_lower in (sme.department or "").lower(),
                q_lower in (sme.role or "").lower(),
            ]):
                continue

        interview_count = await db.scalar(
            select(func.count()).select_from(Interview)
            .where(Interview.sme_id == sme.id)
        )
        approved_count = await db.scalar(
            select(func.count()).select_from(KnowledgeEntry)
            .where(KnowledgeEntry.sme_id == sme.id)
            .where(KnowledgeEntry.status == "approved")
        )
        output.append({
            "sme_id": sme.id,
            "name": sme.name,
            "specialization": sme.specialization,
            "sub_areas": sme.sub_areas,
            "contact_email": sme.contact_email,
            "role": sme.role,
            "department": sme.department,
            "responsible_products": sme.responsible_products,
            "sub_expertise": sme.sub_expertise,
            "created_at": sme.created_at,
            "stats": {
                "interviews": interview_count or 0,
                "approved": approved_count or 0,
            },
        })
    return output


# Knowledge list with multi-filter
@router.get("/admin/knowledge")
async def list_knowledge_filtered(
    sme_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(KnowledgeEntry, SME.name.label("sme_name"))
        .join(SME, KnowledgeEntry.sme_id == SME.id)
        .order_by(KnowledgeEntry.created_at.desc())
    )
    if sme_id:
        query = query.where(KnowledgeEntry.sme_id == sme_id)
    if status:
        query = query.where(KnowledgeEntry.status == status)
    if topic:
        query = query.where(KnowledgeEntry.topic.ilike(f"%{topic}%"))

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": entry.id,
            "topic": entry.topic,
            "sme_id": entry.sme_id,
            "sme_name": sme_name,
            "status": entry.status,
            "created_at": entry.created_at,
        }
        for entry, sme_name in rows
    ]


# Knowledge detail with timeline
@router.get("/admin/knowledge/{entry_id}")
async def get_knowledge_detail(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeEntry, SME.name.label("sme_name"))
        .join(SME, KnowledgeEntry.sme_id == SME.id)
        .where(KnowledgeEntry.id == entry_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    entry, sme_name = row

    timeline = [{"actor": sme_name, "action": "submitted", "at": entry.created_at}]
    if entry.approved_at:
        timeline.append({"actor": sme_name, "action": "sme_approved", "at": entry.approved_at})
    if entry.admin_approved_at:
        timeline.append({"actor": "Admin", "action": "approved", "at": entry.admin_approved_at})
    if entry.rejected_at:
        timeline.append({"actor": "Admin", "action": "rejected", "at": entry.rejected_at})

    return {
        "entry_id": entry.id,
        "sme_id": entry.sme_id,
        "sme_name": sme_name,
        "topic": entry.topic,
        "status": entry.status,
        "content": entry.content,
        "sources": entry.sources_json,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "timeline": timeline,
    }


# Notifications
@router.get("/notifications/sme/unread-counts")
async def get_unread_counts():
    return {"escalated": 0}


# End interview
@router.post("/sme/interviews/{interview_id}/end")
async def end_interview(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = InterviewRepository(db)
    await repo.mark_completed(interview_id)
    return {"interview_id": interview_id, "status": "completed"}
