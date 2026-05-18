from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import verify_token
from app.repositories.material_repository import MaterialRepository
from app.repositories.sme_repository import SMERepository
from app.schemas.material import MaterialListResponse, MaterialRead

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])

_ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _resolve_type(content_type: str | None, filename: str | None) -> str | None:
    """Return a canonical MIME type or None if not accepted."""
    if content_type in _ALLOWED_TYPES:
        # Normalise markdown variant
        return "text/markdown" if "markdown" in content_type else content_type
    # Fallback: infer from extension
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            return "application/pdf"
        if ext == "txt":
            return "text/plain"
        if ext == "md":
            return "text/markdown"
    return None


async def _extract_text(raw: bytes, file_type: str) -> str:
    if file_type == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()
    return raw.decode("utf-8", errors="replace").strip()


async def _embed(mid: str, text: str) -> None:
    try:
        from app.ai_core.embedding_client import EmbeddingService
        from app.db import AsyncSessionLocal
        svc = EmbeddingService()
        chunks = await svc.chunk_and_embed_knowledge(text)
        async with AsyncSessionLocal() as db2:
            await MaterialRepository(db2).store_chunks(mid, chunks)
    except Exception:
        pass


@router.post("/smes/{sme_id}/materials", response_model=MaterialRead, status_code=201)
async def upload_material(
    sme_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    sme = await SMERepository(db).get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")

    file_type = _resolve_type(file.content_type, file.filename)
    if file_type is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                "Accepted: application/pdf, text/plain, text/markdown"
            ),
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    raw_text = await _extract_text(raw, file_type)

    repo = MaterialRepository(db)
    material = await repo.create(
        sme_id=sme_id,
        title=title,
        file_type=file_type,
        raw_text=raw_text,
        description=description,
    )

    background_tasks.add_task(_embed, material.material_id, raw_text)

    return material


@router.get("/smes/{sme_id}/materials", response_model=MaterialListResponse)
async def list_materials(
    sme_id: str,
    db: AsyncSession = Depends(get_db),
):
    sme = await SMERepository(db).get(sme_id)
    if not sme:
        raise HTTPException(status_code=404, detail="SME not found")
    repo = MaterialRepository(db)
    materials = await repo.list_by_sme(sme_id)
    return MaterialListResponse(materials=materials)
