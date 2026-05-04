from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.material_repository import MaterialRepository
from app.repositories.sme_repository import SMERepository
from app.schemas.material import MaterialListResponse

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


@router.get("/smes/{sme_id}/materials", response_model=MaterialListResponse)
async def list_materials(
    sme_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all materials for an SME."""
    sme_repo = SMERepository(db)
    sme = await sme_repo.get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    repo = MaterialRepository(db)
    materials = await repo.list_by_sme(sme_id)
    return MaterialListResponse(materials=materials)
