from starlette.middleware.base import BaseHTTPMiddleware
from app.ai_core.token_tracker import TokenTracker


class TokenTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        TokenTracker.init()
        return await call_next(request)
