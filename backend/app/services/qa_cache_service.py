from dataclasses import dataclass
from app.config import settings


@dataclass
class CacheCheckResult:
    hit_type: str  # "exact" | "soft" | "miss"
    answer: str | None
    cache_id: str | None


class QACacheService:
    def __init__(self, repo):
        self._repo = repo

    async def check(self, question: str, embedding: list[float]) -> CacheCheckResult:
        result = await self._repo.search(
            embedding, settings.QA_CACHE_HIT_THRESHOLD, settings.QA_CACHE_SOFT_THRESHOLD
        )
        hit_type = result["hit_type"]
        row = result["row"]
        if hit_type in ("exact", "soft"):
            return CacheCheckResult(hit_type=hit_type, answer=row.answer, cache_id=row.id)
        return CacheCheckResult(hit_type="miss", answer=None, cache_id=None)

    async def store_async(
        self,
        question: str,
        answer: str,
        embedding: list[float],
        entry_ids: list[str],
        session_id: str | None,
    ) -> None:
        await self._repo.store(question, answer, embedding, entry_ids, session_id)

    async def invalidate(self, entry_id: str) -> None:
        await self._repo.invalidate_by_entry(entry_id)
