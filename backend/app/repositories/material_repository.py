from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.material import Material, MaterialChunk
from app.schemas.material import MaterialRead, MaterialSummary
from app.repositories.utils import new_id


class MaterialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        sme_id: str,
        title: str,
        file_type: str,
        raw_text: str,
        description: str | None = None,
    ) -> MaterialRead:
        material = Material(
            id=new_id("mat"),
            sme_id=sme_id,
            title=title,
            file_type=file_type,
            raw_text=raw_text,
            description=description,
            status="processed",
            exposable=True,
        )
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        return self._to_schema(material)

    async def get(self, material_id: str) -> MaterialRead | None:
        result = await self.db.execute(
            select(Material).where(Material.id == material_id)
        )
        m = result.scalar_one_or_none()
        return self._to_schema(m) if m else None

    async def list_by_sme(self, sme_id: str) -> list[MaterialSummary]:
        result = await self.db.execute(
            select(Material)
            .where(Material.sme_id == sme_id)
            .order_by(Material.created_at.desc())
        )
        return [
            MaterialSummary(
                material_id=m.id,
                title=m.title,
                file_type=m.file_type,
                status=m.status,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]

    async def get_raw_text(self, material_id: str) -> str | None:
        """C 用：取原始文本做 synthesis，不暴露给外部。"""
        result = await self.db.execute(
            select(Material.raw_text).where(Material.id == material_id)
        )
        return result.scalar_one_or_none()

    async def store_chunks(
        self,
        material_id: str,
        chunks: list[tuple[str, list[float]]],
    ) -> None:
        for idx, (chunk_text, embedding) in enumerate(chunks):
            chunk = MaterialChunk(
                id=new_id("chunk"),
                material_id=material_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding,
            )
            self.db.add(chunk)
        await self.db.commit()

    async def search_chunks_by_embedding(
        self,
        query_vector: list[float],
        top_k: int = 5,
        only_exposable: bool = True,
    ):
        vector_str = f"[{','.join(str(x) for x in query_vector)}]"
        exposable_filter = "AND m.exposable = TRUE" if only_exposable else ""
        sql = text(f"""
            SELECT
                mc.chunk_text,
                mc.material_id,
                m.title AS material_title,
                1 - (mc.embedding <=> :vec::vector) AS similarity
            FROM material_chunks mc
            JOIN materials m ON mc.material_id = m.id
            WHERE mc.embedding IS NOT NULL
            {exposable_filter}
            ORDER BY mc.embedding <=> :vec::vector
            LIMIT :k
        """)
        result = await self.db.execute(sql, {"vec": vector_str, "k": top_k})
        return result.fetchall()

    def _to_schema(self, m: Material) -> MaterialRead:
        return MaterialRead(
            material_id=m.id,
            sme_id=m.sme_id,
            title=m.title,
            file_type=m.file_type,
            status=m.status,
            created_at=m.created_at,
        )