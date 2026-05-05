class RetrievalService:
    def __init__(self, kb_repo, sme_repo, embedding):
        self._kb = kb_repo
        self._sme = sme_repo
        self._embedding = embedding

    async def search_kb(self, query_vector: list[float], top_k: int = 5) -> list:
        return await self._kb.search_by_embedding(query_vector, top_k)

    async def search_smes(self, query_vector: list[float], top_k: int = 3) -> list:
        return await self._sme.search_by_embedding(query_vector, top_k)
