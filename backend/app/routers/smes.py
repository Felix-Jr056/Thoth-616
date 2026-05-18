import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.sme_repository import SMERepository
from app.schemas.sme import SMECreate, SMERead, SMEListResponse

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])
logger = logging.getLogger(__name__)


async def _try_embed_sme(sme_id: str) -> None:
    """Background task: embed SME profile and write embedding_status."""
    from app.db import AsyncSessionLocal
    from app.dependencies import embedding
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        try:
            repo = SMERepository(db)
            sme = await repo.get(sme_id)
            if sme is None:
                logger.warning("_try_embed_sme: SME %s not found", sme_id)
                return
            vector = await embedding.embed_sme(sme)
            await repo.update_embedding(sme_id, vector, status="done")
        except Exception:
            logger.exception("_try_embed_sme failed for SME %s", sme_id)
            try:
                async with AsyncSessionLocal() as db2:
                    await SMERepository(db2).update_embedding(sme_id, None, status="failed")
            except Exception:
                pass


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
