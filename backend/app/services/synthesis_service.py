import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from app.ai_core.llm_client import LLMClient
from app.repositories.stub import InterviewRepository
try:
    from app.repositories.knowledge_repository import KnowledgeRepository as KnowledgeEntryRepository
    from app.repositories.knowledge_repository import InvalidStateError
except ImportError:
    from app.repositories.stub import KnowledgeEntryRepository
    class InvalidStateError(Exception):
        pass
from app.schemas.synthesis import SynthesisContent

logger = logging.getLogger(__name__)


class SynthesisService:
    def __init__(
        self,
        interview_repo: InterviewRepository,
        knowledge_repo: KnowledgeEntryRepository,
        llm: LLMClient,
    ):
        self._interview_repo = interview_repo
        self._knowledge_repo = knowledge_repo
        self._llm = llm

    async def synthesize(
        self,
        interview_id: str,
        sme_id: str,
        sme_name: str,
        specialization: str,
    ) -> dict:
        summaries = await self._interview_repo.get_all_topic_summaries(interview_id)
        if not summaries:
            # Fallback: use raw turn responses when no topic summaries exist yet
            data = await self._interview_repo.get_with_turns(interview_id)
            if data and data.get("turns"):
                combined = "\n\n".join(
                    t["sme_response"] for t in data["turns"] if t.get("sme_response")
                )
                summaries = [{"topic_question": specialization, "refined_content": combined}]
        if not summaries:
            raise ValueError(f"No topic summaries or turns found for interview {interview_id}")

        formatted_summaries = "\n\n".join(
            f"Topic {i + 1}: {s['topic_question']}\n{s['refined_content']}"
            for i, s in enumerate(summaries)
        )

        resp = await self._llm.call(
            "synthesis_compose",
            {
                "sme_name": sme_name,
                "specialization": specialization,
                "topic_summaries_formatted": formatted_summaries,
            },
            response_format="json",
        )

        if resp.json is None:
            logger.error("Synthesis JSON parse failed.\nRaw output: %s", resp.text)
            raise ValueError("LLM returned invalid JSON for synthesis_compose")

        raw = resp.json
        raw.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

        # Inject source_interview_id into every topic before schema validation
        for topic in raw.get("topics", []):
            topic.setdefault("source_interview_id", interview_id)

        try:
            content = SynthesisContent.model_validate(raw)
        except ValidationError as e:
            logger.error("Synthesis schema validation failed: %s\nParsed dict: %s", e, raw)
            raise ValueError(f"LLM output does not match expected schema: {e}") from e

        entry = await self._knowledge_repo.create(
            sme_id=sme_id,
            topic=specialization,
            content=content.model_dump_json(),
            sources_json={"interviews": [interview_id], "materials": []},
            source_interview_id=interview_id,
        )

        return {
            "entry_id": entry["id"],
            "content": content.model_dump(),
            "status": entry["status"],
        }

    async def update_entry_status(
        self,
        entry_id: str,
        status: str,
        rejection_reason: str | None = None,
    ) -> None:
        try:
            await self._knowledge_repo.transition_status(
                entry_id, status, reason=rejection_reason
            )
        except InvalidStateError as e:
            raise ValueError(f"Invalid status transition: {e}")
