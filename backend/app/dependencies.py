import os
from app.llm_client import LLMClient
from app.repositories.db_interview_adapter import DBInterviewRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService

# DB-backed repos (persists across restarts)
interview_repo = DBInterviewRepository()

# KnowledgeEntryRepository adapter for C's synthesis_service
# C's service calls: repo.create(...) -> expects dict with ["id"]
# We wrap KnowledgeRepository to return dicts
class _KnowledgeAdapter:
    async def create(
        self,
        sme_id: str,
        topic: str,
        content: str,
        sources_json: dict,
        source_interview_id: str = "",
    ) -> dict:
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            repo = KnowledgeRepository(db)
            result = await repo.create_draft(
                sme_id=sme_id,
                topic=topic,
                content=content,
                source_interview_id=source_interview_id or None,
            )
            return {
                "id": result.entry_id,
                "sme_id": result.sme_id,
                "topic": result.topic,
                "content": result.content,
                "status": result.status,
                "sources_json": sources_json,
                "source_interview_id": source_interview_id,
                "created_at": result.created_at.isoformat(),
            }

    async def get(self, entry_id: str) -> dict | None:
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            repo = KnowledgeRepository(db)
            result = await repo.get(entry_id)
            if result is None:
                return None
            return {
                "id": result.entry_id,
                "sme_id": result.sme_id,
                "topic": result.topic,
                "content": result.content,
                "status": result.status,
            }

    async def transition_status(
        self,
        entry_id: str,
        new_status: str,
        reason: str | None = None,
    ) -> None:
        from app.db import AsyncSessionLocal
        from app.repositories.knowledge_repository import InvalidStateError
        async with AsyncSessionLocal() as db:
            repo = KnowledgeRepository(db)
            await repo.transition_status(entry_id, new_status, reason=reason)

knowledge_repo = _KnowledgeAdapter()

os.environ.setdefault("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "sk-local-placeholder"))
llm = LLMClient()

interview_service = InterviewService(interview_repo=interview_repo, llm=llm)
synthesis_service = SynthesisService(
    interview_repo=interview_repo,
    knowledge_repo=knowledge_repo,
    llm=llm,
)
