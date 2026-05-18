import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.knowledge_repository import KnowledgeRepository, InvalidStateError
from app.schemas.knowledge import (
    KnowledgeRead, KnowledgeListResponse, KnowledgeUpdate,
    KnowledgeReject, KnowledgeApproveResponse,
    KnowledgeAdminApproveResponse, KnowledgeRejectResponse,
    KnowledgeSynthesizeRequest, KnowledgeSynthesizeResponse,
    SourcesSchema,
)
from datetime import datetime, timezone

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

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
    request: Request, entry_id: str, body: KnowledgeUpdate, db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    try:
        result = await repo.update_content(entry_id, body.content)
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    cache = getattr(request.app.state.query_service, "_cache", None)
    if cache is not None:
        await cache.invalidate(entry_id)
    return result


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


async def _try_embed_knowledge(entry_id: str, content: str) -> None:
    """
    Background task: chunk and embed approved knowledge entry.
    D's chunk_and_embed_knowledge(content) returns list of (chunk_text, vector).
    """
    try:
        from app.ai_core.embedding_client import EmbeddingService
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            embedding_service = EmbeddingService()
            chunks = await embedding_service.chunk_and_embed_knowledge(content)
            from app.repositories.knowledge_repository import KnowledgeRepository as KR
            await KR(db).store_chunks(entry_id, chunks)
    except ImportError:
        pass
    except Exception:
        pass


@router.post("/knowledge/{entry_id}/admin-approve", response_model=KnowledgeAdminApproveResponse)
async def admin_approve(
    entry_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    repo = KnowledgeRepository(db)
    try:
        entry = await repo.transition_status(entry_id, "approved")
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Trigger D's embedding pipeline after response is sent
    background_tasks.add_task(_try_embed_knowledge, entry.entry_id, entry.content)

    return KnowledgeAdminApproveResponse(
        entry_id=entry.entry_id,
        status=entry.status,
        admin_approved_at=datetime.now(timezone.utc),
    )


@router.post("/knowledge/{entry_id}/reject", response_model=KnowledgeRejectResponse)
async def reject_knowledge(
    request: Request, entry_id: str, body: KnowledgeReject, db: AsyncSession = Depends(get_db)
):
    repo = KnowledgeRepository(db)
    try:
        entry = await repo.transition_status(entry_id, "rejected", reason=body.reason)
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    except InvalidStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    cache = getattr(request.app.state.query_service, "_cache", None)
    if cache is not None:
        await cache.invalidate(entry_id)
    return KnowledgeRejectResponse(
        entry_id=entry.entry_id,
        status=entry.status,
        rejected_at=datetime.now(timezone.utc),
    )


# ── Knowledge Synthesis ────────────────────────────────────────────────────

async def _synthesize_content(
    sme_name: str,
    specialization: str,
    summaries: list[dict],
    material_texts: list[str],
) -> str:
    """Call LLM to synthesize topic summaries + materials into structured text."""
    from app.dependencies import llm

    parts = []
    for i, s in enumerate(summaries):
        parts.append(f"Topic {i + 1}: {s['topic_question']}\n{s['refined_content']}")
    for j, text in enumerate(material_texts):
        parts.append(f"Supporting Material {j + 1}:\n{text[:4000]}")
    formatted = "\n\n".join(parts)

    response = await llm.call(
        "synthesis_compose",
        {
            "sme_name": sme_name,
            "specialization": specialization,
            "topic_summaries_formatted": formatted,
        },
        response_format="json",
    )

    data = response.json or {}
    try:
        topics = data.get("topics", [])
        out = []
        if data.get("summary"):
            out.append(f"## Summary\n\n{data['summary']}")
        for topic in topics:
            out.append(f"### {topic.get('title', 'Topic')}\n\n{topic.get('content', '')}")
            if topic.get("caveats"):
                out.append("**Caveats:** " + "; ".join(topic["caveats"]))
        return "\n\n".join(out) if out else response.text.strip()
    except (KeyError, TypeError):
        return response.text.strip()


@router.post(
    "/smes/{sme_id}/knowledge/synthesize",
    response_model=KnowledgeSynthesizeResponse,
    status_code=201,
)
async def synthesize_knowledge(
    sme_id: str,
    body: KnowledgeSynthesizeRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.sme_repository import SMERepository
    from app.repositories.interview_repository import InterviewRepository
    from app.repositories.material_repository import MaterialRepository
    from app.ai_core.token_tracker import TokenTracker

    sme = await SMERepository(db).get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")

    # Collect interview topic summaries
    iv_repo = InterviewRepository(db)
    all_summaries: list[dict] = []
    for iid in body.interview_ids:
        summaries = await iv_repo.get_all_topic_summaries(iid)
        all_summaries.extend(summaries)

    # Collect material raw texts
    mat_repo = MaterialRepository(db)
    material_texts: list[str] = []
    for mid in body.material_ids:
        text = await mat_repo.get_raw_text(mid)
        if text:
            material_texts.append(text)

    if not all_summaries and not material_texts:
        raise HTTPException(
            status_code=422,
            detail="No content available: interviews have no topic summaries and no materials found.",
        )

    content = await _synthesize_content(
        sme_name=sme.name,
        specialization=sme.specialization,
        summaries=all_summaries,
        material_texts=material_texts,
    )

    sources = {"interviews": body.interview_ids, "materials": body.material_ids}
    kb_repo = KnowledgeRepository(db)
    entry = await kb_repo.create_draft(
        sme_id=sme_id,
        topic=body.topic,
        content=content,
        sources=sources,
    )

    return KnowledgeSynthesizeResponse(
        entry_id=entry.entry_id,
        sme_id=entry.sme_id,
        topic=entry.topic,
        status=entry.status,
        content=content,
        sources=SourcesSchema(interviews=body.interview_ids, materials=body.material_ids),
        created_at=entry.created_at,
        usage=TokenTracker.collect(),
    )
