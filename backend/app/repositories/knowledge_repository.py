from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone
from app.models.knowledge import KnowledgeEntry, KnowledgeChunk
from app.schemas.knowledge import KnowledgeRead, SourcesSchema
from app.repositories.utils import new_id
from app.models.sme import SME


ALLOWED_TRANSITIONS = {
    ("draft", "sme_approved"),
    ("sme_approved", "approved"),
    ("draft", "rejected"),
    ("sme_approved", "rejected"),
    ("approved", "rejected"),
}


class InvalidStateError(Exception):
    pass


class KnowledgeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_draft(
        self,
        sme_id: str,
        topic: str,
        content: str,
        sources: dict | None = None,
        source_interview_id: str | None = None,
    ) -> KnowledgeRead:
        if sources is None:
            sources = {
                "interviews": [source_interview_id] if source_interview_id else [],
                "materials": []
            }
        entry = KnowledgeEntry(
            id=new_id("ke"),
            sme_id=sme_id,
            topic=topic,
            content=content,
            status="draft",
            sources_json=sources,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return self._to_schema(entry)

    async def get(self, entry_id: str) -> KnowledgeRead | None:
        result = await self.db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        return self._to_schema(entry) if entry else None

    async def list_all(self, status: str | None = None) -> list[KnowledgeRead]:
        query = select(KnowledgeEntry).order_by(KnowledgeEntry.created_at.desc())
        if status:
            query = query.where(KnowledgeEntry.status == status)
        result = await self.db.execute(query)
        return [self._to_schema(e) for e in result.scalars().all()]

    async def update_content(self, entry_id: str, content: str) -> KnowledgeRead:
        result = await self.db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")
        entry.content = content
        entry.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(entry)
        return self._to_schema(entry)

    async def transition_status(
        self,
        entry_id: str,
        new_status: str,
        reason: str | None = None,
    ) -> KnowledgeRead:
        result = await self.db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        if (entry.status, new_status) not in ALLOWED_TRANSITIONS:
            raise InvalidStateError(
                f"Cannot transition from '{entry.status}' to '{new_status}'"
            )

        now = datetime.now(timezone.utc)
        entry.status = new_status
        entry.updated_at = now

        if new_status == "sme_approved":
            entry.approved_at = now
        elif new_status == "approved":
            entry.admin_approved_at = now
        elif new_status == "rejected":
            entry.rejected_at = now
            entry.rejection_reason = reason

        await self.db.commit()
        await self.db.refresh(entry)
        return self._to_schema(entry)

    async def store_chunks(
        self,
        entry_id: str,
        chunks: list[tuple[str, list[float]]],
    ) -> None:
        for idx, (chunk_text, embedding) in enumerate(chunks):
            chunk = KnowledgeChunk(
                id=new_id("kchunk"),
                entry_id=entry_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding,
            )
            self.db.add(chunk)
        await self.db.commit()

    async def search_by_embedding(
        self, query_vector: list[float], top_k: int = 5
    ):
        vector_str = f"[{','.join(str(x) for x in query_vector)}]"
        sql = text("""
            SELECT
                kc.chunk_text,
                ke.id AS entry_id,
                ke.topic,
                ke.sme_id,
                s.name AS sme_name,
                1 - (kc.embedding <=> CAST(:vec AS vector)) AS similarity
            FROM knowledge_chunks kc
            JOIN knowledge_entries ke ON kc.entry_id = ke.id
            JOIN smes s ON ke.sme_id = s.id
            WHERE kc.embedding IS NOT NULL
              AND ke.status = 'approved'
            ORDER BY kc.embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """)
        result = await self.db.execute(sql, {"vec": vector_str, "k": top_k})
        return result.fetchall()

    async def get_topics_by_sme(self, sme_id: str) -> list[str]:
        """返回某 SME 已 approved 的知识主题，供前端显示 recorded_topics。"""
        result = await self.db.execute(
            select(KnowledgeEntry.topic)
            .where(KnowledgeEntry.sme_id == sme_id)
            .where(KnowledgeEntry.status == "approved")
        )
        return [row[0] for row in result.fetchall()]

    async def get_sources_for_entries(self, entry_ids: list[str]) -> list[dict]:
        if not entry_ids:
            return []
        result = await self.db.execute(
            select(KnowledgeEntry.id, KnowledgeEntry.topic, SME.name.label("sme_name"))
            .join(SME, KnowledgeEntry.sme_id == SME.id)
            .where(KnowledgeEntry.id.in_(entry_ids))
        )
        return [
            {"entry_id": row.id, "topic": row.topic, "sme_name": row.sme_name}
            for row in result.fetchall()
        ]

    def _to_schema(self, entry: KnowledgeEntry) -> KnowledgeRead:
        return KnowledgeRead(
            entry_id=entry.id,
            sme_id=entry.sme_id,
            topic=entry.topic,
            status=entry.status,
            content=entry.content,
            sources=SourcesSchema(**entry.sources_json),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )