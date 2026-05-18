from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.qa_cache import QACache
from app.repositories.utils import new_id


class QACacheRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, embedding: list[float], threshold_hard: float, threshold_soft: float
    ) -> dict:
        vec_str = f"[{','.join(str(x) for x in embedding)}]"
        sql = text("""
            SELECT id, answer, 1 - (question_embedding <=> CAST(:vec AS vector)) AS similarity
            FROM qa_cache
            ORDER BY question_embedding <=> CAST(:vec AS vector)
            LIMIT 1
        """)
        result = await self.db.execute(sql, {"vec": vec_str})
        row = result.fetchone()
        if row is None:
            return {"hit_type": "miss", "row": None}
        sim = float(row.similarity)
        if sim >= threshold_hard:
            return {"hit_type": "exact", "row": row}
        if sim >= threshold_soft:
            return {"hit_type": "soft", "row": row}
        return {"hit_type": "miss", "row": None}

    async def store(
        self,
        question: str,
        answer: str,
        embedding: list[float],
        entry_ids: list[str],
        session_id: str | None,
    ) -> None:
        cache = QACache(
            id=new_id("qac"),
            question=question,
            answer=answer,
            question_embedding=embedding,
            source_entry_ids=entry_ids or [],
            session_id=session_id,
        )
        self.db.add(cache)
        await self.db.commit()

    async def invalidate_by_entry(self, entry_id: str) -> None:
        await self.db.execute(
            text("DELETE FROM qa_cache WHERE :entry_id = ANY(source_entry_ids)"),
            {"entry_id": entry_id},
        )
        await self.db.commit()

    async def increment_hit(self, cache_id: str) -> None:
        await self.db.execute(
            text(
                "UPDATE qa_cache SET hit_count = hit_count + 1, last_hit_at = :now WHERE id = :id"
            ),
            {"id": cache_id, "now": datetime.now(timezone.utc)},
        )
        await self.db.commit()
