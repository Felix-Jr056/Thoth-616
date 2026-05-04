from fastapi import APIRouter, HTTPException

from app.dependencies import synthesis_service
from app.schemas.synthesis import SynthesisRequest, SynthesisResponse

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


@router.post("", response_model=SynthesisResponse)
async def synthesize(body: SynthesisRequest):
    try:
        return await synthesis_service.synthesize(
            interview_id=body.interview_id,
            sme_id=body.sme_id,
            sme_name=body.sme_name,
            specialization=body.specialization,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
