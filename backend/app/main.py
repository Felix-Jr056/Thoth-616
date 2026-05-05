import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.tokens import TokenTrackingMiddleware
from app.routers import smes, knowledge, system, admin, interviews, materials
from app.routers import interview, synthesis, query
from app.routers.stubs import router as stubs_router

PROMPTS_DIR = Path(__file__).parent / "prompts"

app = FastAPI(title="Project Thoth API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TokenTrackingMiddleware)

app.include_router(smes.router)
app.include_router(knowledge.router)
app.include_router(system.router)
app.include_router(admin.router)
app.include_router(interviews.router)
app.include_router(materials.router)
app.include_router(interview.router)
app.include_router(synthesis.router)
app.include_router(query.router)
app.include_router(stubs_router)


def _build_query_service():
    from app.ai_core.prompt_loader import PromptLoader
    from app.ai_core.model_router import ModelRouter
    from app.ai_core.llm_client import LLMClient as DLLMClient
    from app.ai_core.embedding_client import EmbeddingService
    from app.services.retrieval_service import RetrievalService
    from app.services.query_service import QueryService
    from app.db import AsyncSessionLocal

    loader = PromptLoader(PROMPTS_DIR)
    model_router = ModelRouter()
    llm = DLLMClient(prompt_loader=loader, model_router=model_router)
    embedding = EmbeddingService()

    class _DBKBRepo:
        async def search_by_embedding(self, query_vector, top_k=5):
            async with AsyncSessionLocal() as db:
                from app.repositories.knowledge_repository import KnowledgeRepository
                return await KnowledgeRepository(db).search_by_embedding(query_vector, top_k)

    class _DBSMERepo:
        async def list_all(self):
            async with AsyncSessionLocal() as db:
                from app.repositories.sme_repository import SMERepository
                smes = await SMERepository(db).list_all()
                # Convert SMERead (Pydantic) to objects D's QueryService can use
                # D needs: .specialization, .sub_areas, .name, .sme_id
                return smes  # SMERead already has all these fields

        async def search_by_embedding(self, query_vector, top_k=3):
            async with AsyncSessionLocal() as db:
                from app.repositories.sme_repository import SMERepository
                results = await SMERepository(db).search_by_embedding(query_vector, top_k)
                # A's search_by_embedding returns [(SMERead, float), ...]
                # D's RetrievalService expects objects with .similarity attribute
                # Wrap into compatible objects
                class _SMEResult:
                    def __init__(self, sme, similarity):
                        self.sme_id = sme.sme_id
                        self.name = sme.name
                        self.specialization = sme.specialization
                        self.sub_areas = sme.sub_areas
                        self.similarity = similarity
                return [_SMEResult(sme, sim) for sme, sim in results]

    class _DBSessionRepo:
        async def get_or_create(self, session_id: str):
            async with AsyncSessionLocal() as db:
                from app.repositories.session_repository import SessionRepository
                return await SessionRepository(db).get_or_create(session_id)

        async def set_pending(self, session_id: str, last_question: str, pending_context: dict):
            async with AsyncSessionLocal() as db:
                from app.repositories.session_repository import SessionRepository
                await SessionRepository(db).set_pending(session_id, last_question, pending_context)

        async def clear_pending(self, session_id: str):
            async with AsyncSessionLocal() as db:
                from app.repositories.session_repository import SessionRepository
                await SessionRepository(db).clear_pending(session_id)

        async def clear_all(self):
            async with AsyncSessionLocal() as db:
                from app.repositories.session_repository import SessionRepository
                await SessionRepository(db).clear_all()

    kb_repo = _DBKBRepo()
    sme_repo = _DBSMERepo()
    session_repo = _DBSessionRepo()

    retrieval = RetrievalService(kb_repo=kb_repo, sme_repo=sme_repo, embedding=embedding)
    return QueryService(
        retrieval=retrieval,
        llm_client=llm,
        session_repo=session_repo,
        embedding=embedding,
        sme_repo=sme_repo,
    )


# Initialize after function is defined
app.state.query_service = _build_query_service()


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


if os.getenv("ENV", "dev") == "dev":
    @app.post("/dev/seed", tags=["dev"])
    async def run_seed():
        from app.tests.seed_test_data import seed
        await seed()
        return {"ok": True}
