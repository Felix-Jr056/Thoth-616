from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.session_repository import SessionRepository

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


@router.post("/system/purge")
async def purge(db: AsyncSession = Depends(get_db)):
    await db.execute(text("""
        TRUNCATE knowledge_chunks, material_chunks, interview_turns,
        sessions, knowledge_entries, materials, interviews, smes
        RESTART IDENTITY CASCADE
    """))
    await db.commit()
    return {"status": "purged", "message": "All data deleted"}


@router.post("/system/reset")
async def reset(db: AsyncSession = Depends(get_db)):
    repo = SessionRepository(db)
    await repo.clear_all()
    return {"status": "reset", "message": "Session state cleared"}