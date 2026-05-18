import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.session_repository import SessionRepository

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])
logger = logging.getLogger(__name__)


@router.post("/system/purge")
async def purge(request: Request, db: AsyncSession = Depends(get_db)):
    caller_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.warning(
        "PURGE called at %s | ip=%s | user-agent=%s",
        timestamp, caller_ip, user_agent,
    )

    await db.execute(text("""
        TRUNCATE
            qa_cache,
            knowledge_chunks,
            material_chunks,
            interview_turns,
            interview_topic_summaries,
            user_query_log,
            sessions,
            knowledge_entries,
            materials,
            interviews,
            smes
        RESTART IDENTITY CASCADE
    """))
    await db.commit()

    from app.dependencies import interview_service
    interview_service._state.clear()

    logger.warning("PURGE complete — all tables truncated")
    return {"status": "purged", "message": "All data deleted"}


@router.post("/system/reset")
async def reset(request: Request, db: AsyncSession = Depends(get_db)):
    caller_ip = request.client.host if request.client else "unknown"
    logger.info("RESET called | ip=%s", caller_ip)
    repo = SessionRepository(db)
    await repo.clear_all()
    return {"status": "reset", "message": "Session state cleared"}