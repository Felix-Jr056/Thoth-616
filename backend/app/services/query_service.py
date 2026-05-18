import asyncio
from datetime import datetime, timezone

from app.config import settings

DISCLAIMER = (
    "This information is based on approved expert knowledge "
    "and does not constitute professional advice."
)
# kb_max >= _KB_SKIP_CLARIFY → skip clarify_prompt (high-confidence, answer directly)
# kb_max in [KB_SIMILARITY_THRESHOLD, _KB_SKIP_CLARIFY) → run clarify_prompt, then answer if "ready"
_KB_SKIP_CLARIFY = 0.65
_MULTI_SME_GAP = 0.05
_MAX_CLARIFY_TRIES = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_kb(results) -> str:
    if not results:
        return "No relevant knowledge found."
    return "\n".join(
        f"[{r.entry_id}] (similarity: {r.similarity:.2f}) {r.topic}: {r.chunk_text}"
        for r in results
    )


def _format_sme_list(sme_results) -> str:
    if not sme_results:
        return "No SMEs available."
    lines = []
    for r in sme_results:
        sme = r[0] if isinstance(r, tuple) else r
        lines.append(f"- {sme.name} | {sme.specialization} | sub-areas: {', '.join(sme.sub_areas)}")
    return "\n".join(lines)


class QueryService:
    def __init__(self, retrieval, llm_client, session_repo, embedding, sme_repo=None, qa_cache=None, query_log=None):
        self._retrieval = retrieval
        self._llm = llm_client
        self._session_repo = session_repo
        self._embedding = embedding
        self._sme_repo = sme_repo
        self._cache = qa_cache  # QACacheService | None
        self._query_log = query_log  # QueryLogRepository adapter | None

    async def _get_database_topics(self) -> list[str]:
        if self._sme_repo is None:
            return []
        smes = await self._sme_repo.list_all()
        return [
            f"{s.specialization} — sub-areas: {', '.join(s.sub_areas)}"
            for s in smes
        ]

    def _log(self, question: str, session_id: str, response_type: str) -> None:
        if self._query_log is not None:
            asyncio.create_task(self._query_log.log(question, session_id, response_type))

    async def handle_query(self, question: str, session_id: str) -> dict:
        session = await self._session_repo.get_or_create(session_id)

        # Restore context if previous turn was a clarifying question
        tries = (session.pending_context or {}).get("clarify_tries", 0) if hasattr(session, "pending_context") else 0
        if session.pending_clarification:
            question = f"{session.last_question} [clarification: {question}]"
            await self._session_repo.clear_pending(session_id)

        # Embed once — used for all retrieval and cache lookup
        query_vec = await self._embedding.embed_text(question)

        # QA cache check — exact hit short-circuits before any LLM call
        cache_hint: str | None = None
        cache_result_id: str | None = None
        if self._cache is not None:
            cache_check = await self._cache.check(question, query_vec)
            if cache_check.hit_type == "exact":
                if cache_check.cache_id:
                    asyncio.create_task(self._cache._repo.increment_hit(cache_check.cache_id))
                # Fix #1: hydrate full sources from stored entry IDs
                sources = []
                if cache_check.source_entry_ids:
                    sources = await self._retrieval.get_sources_for_entries(cache_check.source_entry_ids)
                self._log(question, session_id, "answer")
                return {
                    "answer": cache_check.answer,
                    "grounded": True,
                    "sources": sources,
                    "disclaimer": DISCLAIMER,
                    "session_id": session_id,
                    "response_type": "answer",
                    "routed_to": None,
                    "timestamp": _now_iso(),
                    "usage": None,
                }
            elif cache_check.hit_type == "soft":
                # Pass prior answer as hint context for the LLM
                cache_hint = cache_check.answer
                cache_result_id = cache_check.cache_id

        # Parallel retrieval
        kb_results, sme_results = await asyncio.gather(
            self._retrieval.search_kb(query_vec, top_k=5),
            self._retrieval.search_smes(query_vec, top_k=3),
        )
        kb_max = max((r.similarity for r in kb_results), default=0.0)

        # Fix #3: high-confidence KB hit — skip clarify_prompt entirely
        if kb_max >= _KB_SKIP_CLARIFY:
            result = await self._answer(question, kb_results, session_id, query_vec, cache_hint, cache_result_id)
            self._log(question, session_id, result.get("response_type", "answer"))
            return result

        # Ambiguous zone — run clarify_prompt to classify the query
        database_topics = await self._get_database_topics()
        clarify_resp = await self._llm.call(
            "clarify_prompt",
            inputs={
                "question": question,
                "database_topics": "\n".join(
                    f"- {t}" for t in database_topics
                ) or "No topics defined.",
            },
            response_format="json",
        )
        decision = clarify_resp.json or {}
        path = decision.get("path", "ready")

        # not_related — immediately route to admin; no clarification loop
        if path == "not_related":
            result = await self._route_sme(question, sme_results, session_id)
            self._log(question, session_id, result.get("response_type"))
            return result

        # needs_clarify — loop back (max 2 tries)
        if path == "needs_clarify" and tries < _MAX_CLARIFY_TRIES:
            clarifying_q = decision.get("clarifying_question") or "Could you provide more details?"
            await self._session_repo.set_pending(
                session_id,
                last_question=question,
                pending_context={"clarify_tries": tries + 1},
            )
            self._log(question, session_id, "clarification")
            return {
                "answer": clarifying_q,
                "grounded": False,
                "sources": [],
                "disclaimer": None,
                "session_id": session_id,
                "response_type": "clarification",
                "routed_to": None,
                "timestamp": _now_iso(),
            }

        # Fix #8: use settings threshold (single source of truth)
        if kb_max >= settings.KB_SIMILARITY_THRESHOLD:
            result = await self._answer(question, kb_results, session_id, query_vec, cache_hint, cache_result_id)
        else:
            result = await self._route_sme(question, sme_results, session_id)

        self._log(question, session_id, result.get("response_type"))
        return result

    async def _answer(
        self,
        question: str,
        kb_results,
        session_id: str,
        query_vec: list[float],
        cache_hint: str | None = None,
        cache_result_id: str | None = None,
    ) -> dict:
        # cache_hint is passed as an explicit template variable so that
        # PromptLoader's StrictUndefined does not throw when it is absent.
        # The template's {% if cache_hint %} block handles the empty-string case.
        answer_resp = await self._llm.call(
            "answer_generate",
            inputs={
                "question": question,
                "kb_chunks": _format_kb(kb_results),
                "cache_hint": cache_hint or "",
            },
        )
        sources = [
            {"entry_id": r.entry_id, "sme_name": r.sme_name, "topic": r.topic}
            for r in kb_results
            if r.similarity >= 0.6
        ][:3]
        entry_ids = [r.entry_id for r in kb_results if r.similarity >= 0.6][:3]

        # Store in cache — fire-and-forget
        if self._cache is not None:
            asyncio.create_task(
                self._cache.store_async(
                    question=question,
                    answer=answer_resp.text,
                    embedding=query_vec,
                    entry_ids=entry_ids,
                    session_id=session_id,
                )
            )

        return {
            "answer": answer_resp.text,
            "grounded": True,
            "sources": sources,
            "disclaimer": DISCLAIMER,
            "session_id": session_id,
            "response_type": "answer",
            "routed_to": None,
            "timestamp": _now_iso(),
        }

    async def _route_sme(self, question: str, sme_results, session_id: str) -> dict:
        route_resp = await self._llm.call(
            "sme_prompt",
            inputs={
                "question": question,
                "sme_list": _format_sme_list(sme_results),
            },
            response_format="json",
        )
        data = route_resp.json or {}
        answer = data.get("answer", "Routing you to the appropriate expert.")
        routed_to = data.get("routed_to", [
            {"type": "admin", "sme_name": None,
             "specialization": "General Administration",
             "reason": "No SME currently covers this topic."}
        ])
        return {
            "answer": answer,
            "grounded": False,
            "sources": [],
            "disclaimer": None,
            "session_id": session_id,
            "response_type": "routing",
            "routed_to": routed_to,
            "timestamp": _now_iso(),
        }
