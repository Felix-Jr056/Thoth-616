"""
Temporary in-memory repos for D to develop and test independently.
Replace with A's real Repository classes once the DB is ready.

Usage:
    from app.services.mock_repos import MockKnowledgeRepo, MockSMERepo, MockSessionRepo
    # swap out when A's repos land:
    # from app.repositories.knowledge import KnowledgeRepository as MockKnowledgeRepo
"""
import math
from dataclasses import dataclass, field
from typing import Optional


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class _KBEntry:
    entry_id: str
    topic: str
    sme_id: str
    sme_name: str
    chunk_text: str
    embedding: list[float]


@dataclass
class _SMEEntry:
    sme_id: str
    name: str
    specialization: str
    sub_areas: list[str]
    embedding: list[float]


@dataclass
class _Session:
    session_id: str
    pending_clarification: bool = False
    last_question: Optional[str] = None
    pending_context: dict = field(default_factory=dict)


class _KBResult:
    def __init__(self, entry: _KBEntry, similarity: float):
        self.entry_id = entry.entry_id
        self.topic = entry.topic
        self.sme_id = entry.sme_id
        self.sme_name = entry.sme_name
        self.chunk_text = entry.chunk_text
        self.similarity = similarity


class _SMEResult:
    def __init__(self, sme: _SMEEntry, similarity: float):
        self.sme_id = sme.sme_id
        self.name = sme.name
        self.specialization = sme.specialization
        self.sub_areas = sme.sub_areas
        self.similarity = similarity


class MockKnowledgeRepo:
    def __init__(self):
        self._entries: list[_KBEntry] = []

    def add(self, entry_id: str, topic: str, sme_id: str, sme_name: str,
            chunk_text: str, embedding: list[float]):
        self._entries.append(_KBEntry(entry_id, topic, sme_id, sme_name, chunk_text, embedding))

    async def search_by_embedding(self, query_vector: list[float], top_k: int = 5) -> list[_KBResult]:
        scored = [(_cosine(query_vector, e.embedding), e) for e in self._entries]
        scored.sort(key=lambda x: -x[0])
        return [_KBResult(e, sim) for sim, e in scored[:top_k]]


class MockSMERepo:
    def __init__(self):
        self._smes: list[_SMEEntry] = []

    def add(self, sme_id: str, name: str, specialization: str,
            sub_areas: list[str], embedding: list[float]):
        self._smes.append(_SMEEntry(sme_id, name, specialization, sub_areas, embedding))

    async def list_all(self) -> list[_SMEEntry]:
        return list(self._smes)

    async def search_by_embedding(self, query_vector: list[float], top_k: int = 3):
        scored = [(_cosine(query_vector, s.embedding), s) for s in self._smes]
        scored.sort(key=lambda x: -x[0])
        return [_SMEResult(s, sim) for sim, s in scored[:top_k]]


class MockSessionRepo:
    def __init__(self):
        self._sessions: dict[str, _Session] = {}

    async def get_or_create(self, session_id: str) -> _Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = _Session(session_id=session_id)
        return self._sessions[session_id]

    async def set_pending(self, session_id: str, last_question: str, pending_context: dict):
        s = await self.get_or_create(session_id)
        s.pending_clarification = True
        s.last_question = last_question
        s.pending_context = pending_context

    async def clear_pending(self, session_id: str):
        s = await self.get_or_create(session_id)
        s.pending_clarification = False
        s.last_question = None
        s.pending_context = {}

    async def clear_all(self):
        self._sessions.clear()
