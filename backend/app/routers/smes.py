from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.sme_repository import SMERepository
from app.schemas.sme import SMECreate, SMERead, SMEListResponse

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


async def _try_embed_sme(sme_id: str) -> None:
    """Background task: embed SME profile. Safe to fail - D provides this later."""
    try:
        from app.services.embedding_service import EmbeddingService
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            embedding_service = EmbeddingService()
            await embedding_service.embed_sme(sme_id, db)
    except ImportError:
        pass  # EmbeddingService not yet available
    except Exception:
        pass  # Never let background task crash the request


@router.post("/smes", response_model=SMERead, status_code=201)
async def create_sme(
    body: SMECreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    repo = SMERepository(db)
    sme = await repo.create(
        name=body.name,
        specialization=body.specialization,
        sub_areas=body.sub_areas,
        contact_email=body.contact_email,
        role=body.role,
        department=body.department,
        responsible_products=body.responsible_products,
        sub_expertise=body.sub_expertise,
    )
    # Hook for Person D: runs after response is sent, uses its own DB session
    background_tasks.add_task(_try_embed_sme, sme.sme_id)
    return sme


@router.get("/smes", response_model=SMEListResponse)
async def list_smes(db: AsyncSession = Depends(get_db)):
    repo = SMERepository(db)
    smes = await repo.list_all()
    return SMEListResponse(smes=smes)


@router.get("/smes/{sme_id}", response_model=SMERead)
async def get_sme(sme_id: str, db: AsyncSession = Depends(get_db)):
    repo = SMERepository(db)
    sme = await repo.get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    return sme
