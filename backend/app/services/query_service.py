import asyncio
from datetime import datetime, timezone

DISCLAIMER = (
    "This information is based on approved expert knowledge "
    "and does not constitute professional advice."
)
_ANSWER_THRESHOLD = 0.7
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
    def __init__(self, retrieval, llm_client, session_repo, embedding, sme_repo=None):
        self._retrieval = retrieval
        self._llm = llm_client
        self._session_repo = session_repo
        self._embedding = embedding
        self._sme_repo = sme_repo  # used to fetch live topic list on every query

    async def _get_database_topics(self) -> list[str]:
        if self._sme_repo is None:
            return []
        smes = await self._sme_repo.list_all()
        return [
            f"{s.specialization} — sub-areas: {', '.join(s.sub_areas)}"
            for s in smes
        ]

    async def handle_query(self, question: str, session_id: str) -> dict:
        session = await self._session_repo.get_or_create(session_id)

        # Restore context if previous turn was a clarifying question
        tries = (session.pending_context or {}).get("clarify_tries", 0) if hasattr(session, "pending_context") else 0
        if session.pending_clarification:
            question = f"{session.last_question} [clarification: {question}]"
            await self._session_repo.clear_pending(session_id)

        # Embed once — used for all retrieval
        query_vec = await self._embedding.embed_text(question)

        # Parallel retrieval
        kb_results, sme_results = await asyncio.gather(
            self._retrieval.search_kb(query_vec, top_k=5),
            self._retrieval.search_smes(query_vec, top_k=3),
        )

        # Step 1: Haiku decides path via clarify_prompt (topics fetched live from DB)
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

        # not_related or needs_clarify — loop back (max 2 tries)
        if path in ("not_related", "needs_clarify") and tries < _MAX_CLARIFY_TRIES:
            clarifying_q = decision.get("clarifying_question") or (
                "Could you clarify your question? It doesn't seem to match our knowledge base topics."
                if path == "not_related"
                else "Could you provide more details?"
            )
            await self._session_repo.set_pending(
                session_id,
                last_question=question,
                pending_context={"clarify_tries": tries + 1},
            )
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

        # Step 2: ready (or max tries reached) — check kb_max
        kb_max = max((r.similarity for r in kb_results), default=0.0)

        if kb_max >= _ANSWER_THRESHOLD:
            return await self._answer(question, kb_results, session_id)
        else:
            return await self._route_sme(question, sme_results, session_id)

    async def _answer(self, question: str, kb_results, session_id: str) -> dict:
        answer_resp = await self._llm.call(
            "answer_generate",
            inputs={
                "question": question,
                "kb_chunks": _format_kb(kb_results),
            },
        )
        sources = [
            {"entry_id": r.entry_id, "sme_name": r.sme_name, "topic": r.topic}
            for r in kb_results
            if r.similarity >= 0.6
        ][:3]
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
