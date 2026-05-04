from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.knowledge_repository import KnowledgeRepository, InvalidStateError
from app.schemas.knowledge import (
    KnowledgeRead, KnowledgeListResponse, KnowledgeUpdate,
    KnowledgeReject, KnowledgeApproveResponse,
    KnowledgeAdminApproveResponse, KnowledgeRejectResponse,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


@router.get("/knowledge", response_model=KnowledgeListResponse)
async def list_knowledge(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    entries = await repo.list_all(status=status)
    return KnowledgeListResponse(entries=entries)


@router.get("/knowledge/{entry_id}", response_model=KnowledgeRead)
async def get_knowledge(entry_id: str, db: AsyncSession = Depends(get_db)):
    repo = KnowledgeRepository(db)
    entry = await repo.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.put("/knowledge/{entry_id}", response_model=KnowledgeRead)
async def update_knowledge(
    entry_id: str, body: KnowledgeUpdate, db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    try:
        return await repo.update_content(entry_id, body.content)
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")


@router.post("/knowledge/{entry_id}/approve", response_model=KnowledgeApproveResponse)
async def sme_approve(entry_id: str, db: AsyncSession = Depends(get_db)):
    repo = KnowledgeRepository(db)
    try:
        entry = await repo.transition_status(entry_id, "sme_approved")
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return KnowledgeApproveResponse(
        entry_id=entry.entry_id,
        status=entry.status,
        approved_at=datetime.now(timezone.utc),
    )


@router.post("/knowledge/{entry_id}/admin-approve", response_model=KnowledgeAdminApproveResponse)
async def admin_approve(entry_id: str, db: AsyncSession = Depends(get_db)):
    repo = KnowledgeRepository(db)
    try:
        entry = await repo.transition_status(entry_id, "approved")
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Hook for Person D: chunk and embed approved knowledge entry
    # D will replace this block with the real EmbeddingService call
    try:
        from app.services.embedding_service import EmbeddingService  # D provides this
        embedding_service = EmbeddingService()
        await embedding_service.chunk_and_embed_knowledge(entry_id, db)
    except ImportError:
        pass  # EmbeddingService not yet available - safe to skip during development

    return KnowledgeAdminApproveResponse(
        entry_id=entry.entry_id,
        status=entry.status,
        admin_approved_at=datetime.now(timezone.utc),
    )


@router.post("/knowledge/{entry_id}/reject", response_model=KnowledgeRejectResponse)
async def reject_knowledge(
    entry_id: str, body: KnowledgeReject, db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    try:
        entry = await repo.transition_status(entry_id, "rejected", reason=body.reason)
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return KnowledgeRejectResponse(
        entry_id=entry.entry_id,
        status=entry.status,
        rejected_at=datetime.now(timezone.utc),
    )