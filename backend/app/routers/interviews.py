import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.interview_repository import InterviewRepository
from app.dependencies import interview_service
from app.schemas.interview import (
    InterviewCreate, InterviewRead, InterviewListResponse,
    InterviewWithTurns, InterviewTurnCreate, InterviewTurnResponse
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


@router.post("/smes/{sme_id}/interviews", response_model=InterviewRead, status_code=201)
async def create_interview(
    sme_id: str,
    body: InterviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new interview record, then kick off background LLM initialisation."""
    repo = InterviewRepository(db)
    from app.repositories.sme_repository import SMERepository
    sme_repo = SMERepository(db)
    sme = await sme_repo.get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    interview = await repo.create(sme_id=sme_id, topic=body.topic, agenda=[body.topic])
    asyncio.create_task(
        interview_service.initialize_from_benchmark(interview.interview_id, sme, body.topic)
    )
    return interview


@router.get("/smes/{sme_id}/interviews", response_model=InterviewListResponse)
async def list_interviews(
    sme_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all interviews for an SME (no turns)."""
    repo = InterviewRepository(db)
    interviews = await repo.list_by_sme(sme_id)
    return InterviewListResponse(interviews=interviews)


@router.get("/interviews/{interview_id}", response_model=InterviewWithTurns)
async def get_interview(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full interview with all turns."""
    repo = InterviewRepository(db)
    result = await repo.get_with_turns(interview_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interview not found")
    return result


@router.post("/interviews/{interview_id}/turns", response_model=None)
async def submit_interview_turn(
    interview_id: str,
    body: InterviewTurnCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Benchmark endpoint: submit SME answer, get AI follow-up.
    Delegates to C's InterviewService for LLM logic.
    """
    from app.ai_core.token_tracker import TokenTracker
    TokenTracker.init()

    result = await interview_service.submit_answer(
        interview_id=interview_id,
        sme_response=body.sme_response,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Map C's response format to benchmark spec
    turn_number = result.get("turn_number", 1)
    follow_up = result.get("question")  # None if completed

    return {
        "turn_number": turn_number,
        "sme_response": body.sme_response,
        "agent_follow_up": follow_up,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "usage": TokenTracker.collect() or result.get("usage"),
    }
