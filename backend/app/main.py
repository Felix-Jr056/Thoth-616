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


@app.on_event("startup")
async def startup():
    app.state.query_service = _build_query_service()


def _build_query_service():
    from app.ai_core.prompt_loader import PromptLoader
    from app.ai_core.model_router import ModelRouter
    from app.ai_core.llm_client import LLMClient
    from app.ai_core.embedding_client import EmbeddingService
    from app.services.retrieval_service import RetrievalService
    from app.services.query_service import QueryService
    from app.services.mock_repos import MockKnowledgeRepo, MockSMERepo, MockSessionRepo

    loader = PromptLoader(PROMPTS_DIR)
    router = ModelRouter()
    llm = LLMClient(prompt_loader=loader, model_router=router)
    embedding = EmbeddingService()

    # Swap these for A's real repositories once DB wiring is confirmed
    kb_repo = MockKnowledgeRepo()
    sme_repo = MockSMERepo()
    session_repo = MockSessionRepo()

    retrieval = RetrievalService(kb_repo=kb_repo, sme_repo=sme_repo, embedding=embedding)
    return QueryService(
        retrieval=retrieval, llm_client=llm,
        session_repo=session_repo, embedding=embedding,
        sme_repo=sme_repo,
    )


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
