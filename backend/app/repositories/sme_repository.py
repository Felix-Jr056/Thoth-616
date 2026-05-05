from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.sme import SME
from app.schemas.sme import SMERead
from app.repositories.utils import new_id


class SMERepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        specialization: str,
        sub_areas: list[str],
        contact_email: str,
        role: str | None = None,
        department: str | None = None,
        responsible_products: list[str] | None = None,
        sub_expertise: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> SMERead:
        sme = SME(
            id=new_id("sme"),
            name=name,
            specialization=specialization,
            sub_areas=sub_areas,
            contact_email=contact_email,
            role=role,
            department=department,
            responsible_products=responsible_products,
            sub_expertise=sub_expertise,
            embedding=embedding,
        )
        self.db.add(sme)
        await self.db.commit()
        await self.db.refresh(sme)
        return self._to_schema(sme)

    async def get(self, sme_id: str) -> SMERead | None:
        result = await self.db.execute(select(SME).where(SME.id == sme_id))
        sme = result.scalar_one_or_none()
        return self._to_schema(sme) if sme else None

    async def list_all(self) -> list[SMERead]:
        result = await self.db.execute(select(SME).order_by(SME.created_at.desc()))
        return [self._to_schema(s) for s in result.scalars().all()]

    async def update_embedding(self, sme_id: str, embedding: list[float]) -> None:
        result = await self.db.execute(select(SME).where(SME.id == sme_id))
        sme = result.scalar_one_or_none()
        if sme:
            sme.embedding = embedding
            await self.db.commit()

    async def search_by_embedding(
        self, query_vector: list[float], top_k: int = 3
    ) -> list[tuple[SMERead, float]]:
        vector_str = f"[{','.join(str(x) for x in query_vector)}]"
        sql = text("""
            SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM smes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """)
        result = await self.db.execute(sql, {"vec": vector_str, "k": top_k})
        rows = result.fetchall()

        output = []
        for row in rows:
            sme = await self.get(row.id)
            if sme:
                output.append((sme, float(row.similarity)))
        return output

    def _to_schema(self, sme: SME) -> SMERead:
        return SMERead(
            sme_id=sme.id,
            name=sme.name,
            specialization=sme.specialization,
            sub_areas=sme.sub_areas,
            contact_email=sme.contact_email,
            role=sme.role,
            department=sme.department,
            responsible_products=sme.responsible_products,
            sub_expertise=sme.sub_expertise,
            created_at=sme.created_at,
        )