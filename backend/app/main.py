from fastapi import FastAPI
from fastapi.security import HTTPBearer
from datetime import datetime, timezone
from app.routers import smes, knowledge, system, stubs, admin

bearer_scheme = HTTPBearer()

app = FastAPI(
    title="Project Thoth API",
    version="1.0.0",
)

app.include_router(smes.router)
app.include_router(knowledge.router)
app.include_router(system.router)
app.include_router(stubs.router)
app.include_router(admin.router)


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }