"""
Wraps InterviewRepository with its own AsyncSessionLocal session
so it can be used as a module-level singleton in dependencies.py
(same pattern as _KnowledgeAdapter).
"""
from app.repositories.interview_repository import InterviewRepository


class DBInterviewRepository:
    """Drop-in replacement for the in-memory stub. Persists to Postgres."""

    async def _repo(self) -> InterviewRepository:
        from app.db import AsyncSessionLocal
        # Caller is responsible for using this inside an async context
        return None  # resolved per-call below

    # ------------------------------------------------------------------ proxy

    async def create(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).create(*args, **kwargs)

    async def get(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).get(*args, **kwargs)

    async def get_with_turns(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).get_with_turns(*args, **kwargs)

    async def list_by_sme(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).list_by_sme(*args, **kwargs)

    async def add_turn(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).add_turn(*args, **kwargs)

    async def mark_completed(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).mark_completed(*args, **kwargs)

    async def save_topic_summary(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).save_topic_summary(*args, **kwargs)

    async def get_all_topic_summaries(self, *args, **kwargs):
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await InterviewRepository(db).get_all_topic_summaries(*args, **kwargs)
