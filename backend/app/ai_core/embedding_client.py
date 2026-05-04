import os
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

MODEL = "text-embedding-3-small"
DIM = 1024  # matches DB VECTOR(1024) schema; OpenAI supports custom dimensions
_CHARS_PER_TOKEN = 4


def _chunk_text(text: str, target_tokens: int, overlap: int) -> list[str]:
    target_chars = target_tokens * _CHARS_PER_TOKEN
    overlap_chars = overlap * _CHARS_PER_TOKEN
    chunks, start = [], 0
    while start < len(text):
        end = start + target_chars
        chunks.append(text[start:end])
        start = end - overlap_chars
    return [c for c in chunks if c.strip()]


class EmbeddingService:
    def __init__(self, client=None):
        # Embeddings go directly to OpenAI using dedicated OPENAI_API_KEY
        self._client = client or AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    async def embed_text(self, text: str) -> list[float]:
        return (await self._embed([text]))[0]

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        return await self._embed(chunks)

    async def embed_sme(self, sme) -> list[float]:
        text = f"Specialization: {sme.specialization}. Sub-areas: {', '.join(sme.sub_areas)}"
        return await self.embed_text(text)

    async def chunk_and_embed_knowledge(
        self, content: str, target_tokens: int = 400, overlap: int = 80
    ) -> list[tuple[str, list[float]]]:
        chunks = _chunk_text(content, target_tokens, overlap)
        embeddings = await self.embed_chunks(chunks)
        return list(zip(chunks, embeddings))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4))
    async def _embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=MODEL,
            input=texts,
            dimensions=DIM,
        )
        return [item.embedding for item in response.data]
