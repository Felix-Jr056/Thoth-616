_SME_MIN_SIMILARITY = 0.3


class RetrievalService:
    def __init__(self, kb_repo, sme_repo, embedding):
        self._kb = kb_repo
        self._sme = sme_repo
        self._embedding = embedding

    async def search_kb(self, query_vector: list[float], top_k: int = 5) -> list:
        return await self._kb.search_by_embedding(query_vector, top_k)

    async def search_smes(self, query_vector: list[float], top_k: int = 3) -> list:
        results = await self._sme.search_by_embedding(query_vector, top_k)
        max_sim = max((r.similarity for r in results), default=0.0)
        if not results or max_sim < _SME_MIN_SIMILARITY:
            # Vector search returned nothing useful — fall back to full list
            return await self._sme.list_all()
        return results
