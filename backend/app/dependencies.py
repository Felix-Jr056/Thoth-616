from pathlib import Path

from app.ai_core.llm_client import LLMClient
from app.ai_core.model_router import ModelRouter
from app.ai_core.prompt_loader import PromptLoader
from app.ai_core.embedding_client import EmbeddingService
from app.repositories.db_interview_adapter import DBInterviewRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService

PROMPTS_DIR = Path(__file__).parent / "prompts"

# --- Singletons (module-level, instantiated once at startup) ---
_prompt_loader = PromptLoader(PROMPTS_DIR)
_model_router = ModelRouter()

llm = LLMClient(prompt_loader=_prompt_loader, model_router=_model_router)
embedding = EmbeddingService()

# --- DB-backed repos ---
interview_repo = DBInterviewRepository()


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
        async with AsyncSessionLocal() as db:
            repo = KnowledgeRepository(db)
            await repo.transition_status(entry_id, new_status, reason=reason)


knowledge_repo = _KnowledgeAdapter()

interview_service = InterviewService(interview_repo=interview_repo, llm=llm)
synthesis_service = SynthesisService(
    interview_repo=interview_repo,
    knowledge_repo=knowledge_repo,
    llm=llm,
)
