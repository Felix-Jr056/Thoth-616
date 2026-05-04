import os
from fastapi import FastAPI
from datetime import datetime, timezone
from app.routers import smes, knowledge, system, admin, interviews, materials
from app.routers import interview, synthesis
from app.routers.stubs import router as stubs_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Project Thoth API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(smes.router)
app.include_router(knowledge.router)
app.include_router(system.router)
app.include_router(admin.router)
app.include_router(interviews.router)
app.include_router(materials.router)
app.include_router(interview.router)
app.include_router(synthesis.router)
app.include_router(stubs_router)

if os.getenv("ENV", "dev") == "dev":
    @app.post("/dev/seed", tags=["dev"])
    async def run_seed():
        from app.tests.seed_test_data import seed
        await seed()
        return {"ok": True}

@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }