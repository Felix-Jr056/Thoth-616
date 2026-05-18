import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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


# ── Global error shape: benchmark contract requires {"error": "..."} ──────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errs = exc.errors()
    msg = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errs
    )
    return JSONResponse(status_code=422, content={"error": msg})


def _build_query_service():
    from app.dependencies import llm, embedding  # reuse module-level singletons
    from app.services.retrieval_service import RetrievalService
    from app.services.query_service import QueryService
    from app.services.qa_cache_service import QACacheService
    from app.db import AsyncSessionLocal

    class _DBKBRepo:
        async def search_by_embedding(self, query_vector, top_k=5):
            async with AsyncSessionLocal() as db:
                from app.repositories.knowledge_repository import KnowledgeRepository
                return await KnowledgeRepository(db).search_by_embedding(query_vector, top_k)

    class _DBSMERepo:
        async def list_all(self):
            async with AsyncSessionLocal() as db:
                from app.repositories.sme_repository import SMERepository
                return await SMERepository(db).list_all()

        async def search_by_embedding(self, query_vector, top_k=3):
            async with AsyncSessionLocal() as db:
                from app.repositories.sme_repository import SMERepository
                results = await SMERepository(db).search_by_embedding(query_vector, top_k)
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

    class _DBCacheRepo:
        async def search(self, emb, threshold_hard, threshold_soft):
            async with AsyncSessionLocal() as db:
                from app.repositories.qa_cache_repository import QACacheRepository
                return await QACacheRepository(db).search(emb, threshold_hard, threshold_soft)

        async def store(self, question, answer, emb, entry_ids, session_id):
            async with AsyncSessionLocal() as db:
                from app.repositories.qa_cache_repository import QACacheRepository
                await QACacheRepository(db).store(question, answer, emb, entry_ids, session_id)

        async def invalidate_by_entry(self, entry_id: str):
            async with AsyncSessionLocal() as db:
                from app.repositories.qa_cache_repository import QACacheRepository
                await QACacheRepository(db).invalidate_by_entry(entry_id)

        async def increment_hit(self, cache_id: str):
            async with AsyncSessionLocal() as db:
                from app.repositories.qa_cache_repository import QACacheRepository
                await QACacheRepository(db).increment_hit(cache_id)

    kb_repo = _DBKBRepo()
    sme_repo = _DBSMERepo()
    session_repo = _DBSessionRepo()
    cache_repo = _DBCacheRepo()
    qa_cache = QACacheService(repo=cache_repo)

    retrieval = RetrievalService(kb_repo=kb_repo, sme_repo=sme_repo, embedding=embedding)
    return QueryService(
        retrieval=retrieval,
        llm_client=llm,
        session_repo=session_repo,
        embedding=embedding,
        sme_repo=sme_repo,
        qa_cache=qa_cache,
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
