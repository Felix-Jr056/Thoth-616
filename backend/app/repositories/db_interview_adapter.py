"""
Adapter: wraps A's real DB InterviewRepository but returns dicts
so that C's InterviewService works without modification.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.repositories.interview_repository import InterviewRepository as _DBRepo


class DBInterviewRepository:
    """Drop-in replacement for stub.InterviewRepository that persists to DB."""

    def __init__(self):
        # No db session at init time - we create one per call
        pass

    async def _get_repo(self) -> tuple[AsyncSession, _DBRepo]:
        session = AsyncSessionLocal()
        return session, _DBRepo(session)

    async def create(
        self,
        sme_id: str,
        topic: str,
        requested_by: str = "sme",
        admin_note: str = "",
    ) -> dict:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            result = await repo.create(
                sme_id=sme_id,
                topic=topic,
                requested_by=requested_by or None,
                admin_note=admin_note or None,
            )
            return {
                "id": result.interview_id,
                "sme_id": result.sme_id,
                "topic": result.topic,
                "status": result.status,
                "requested_by": requested_by,
                "admin_note": admin_note,
                "created_at": result.created_at.isoformat(),
            }

    async def get_with_turns(self, interview_id: str) -> dict | None:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            result = await repo.get_with_turns(interview_id)
            if result is None:
                return None
            return {
                "interview": {
                    "id": result.interview_id,
                    "sme_id": result.sme_id,
                    "topic": result.topic,
                    "status": result.status,
                },
                "turns": [
                    {
                        "turn_number": t.turn_number,
                        "sme_response": t.sme_response,
                        "agent_follow_up": t.agent_follow_up,
                        "refined_summary": None,
                    }
                    for t in result.turns
                ],
            }

    async def add_turn(
        self,
        interview_id: str,
        sme_response: str,
        agent_follow_up: str | None,
        refined_summary: str = "",
    ) -> dict:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            turn = await repo.add_turn(
                interview_id=interview_id,
                sme_response=sme_response,
                agent_follow_up=agent_follow_up,
                refined_summary=refined_summary,
            )
            return {
                "turn_number": turn.turn_number,
                "sme_response": turn.sme_response,
                "agent_follow_up": turn.agent_follow_up,
                "refined_summary": refined_summary,
            }

    async def mark_completed(self, interview_id: str) -> None:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            await repo.mark_completed(interview_id)

    async def save_topic_summary(
        self,
        interview_id: str,
        topic_index: int,
        topic_question: str,
        refined_content: str,
    ) -> None:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            await repo.save_topic_summary(
                interview_id=interview_id,
                topic_index=topic_index,
                topic_question=topic_question,
                refined_content=refined_content,
            )

    async def get_all_topic_summaries(self, interview_id: str) -> list[dict]:
        async with AsyncSessionLocal() as db:
            repo = _DBRepo(db)
            return await repo.get_all_topic_summaries(interview_id)
