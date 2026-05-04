from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from app.middleware.auth import verify_token
from app.ai_core.token_tracker import TokenTracker

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_token)])


class QueryRequest(BaseModel):
    question: str
    session_id: str


@router.post("/query")
async def query(req: QueryRequest, request: Request):
    svc = request.app.state.query_service
    response = await svc.handle_query(req.question, req.session_id)
    response["usage"] = TokenTracker.collect()
    return response
