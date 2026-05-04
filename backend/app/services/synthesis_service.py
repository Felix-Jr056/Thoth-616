import json
import logging
from datetime import datetime, timezone
from pathlib import Path

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

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


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
            raise ValueError(f"No topic summaries found for interview {interview_id}")

        formatted = "\n\n".join(
            f"Topic {i + 1}: {s['topic_question']}\n{s['refined_content']}"
            for i, s in enumerate(summaries)
        )

        template = _load_prompt("synthesis_generate.md")
        prompt = (
            template
            .replace("{sme_name}", sme_name)
            .replace("{specialization}", specialization)
            .replace("{topic_summaries_formatted}", formatted)
        )

        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.synthesis_model,
            max_tokens=4000,
        )

        try:
            raw = json.loads(response.content.strip())
        except json.JSONDecodeError as e:
            logger.error("Synthesis JSON parse failed: %s\nRaw output: %s", e, response.content)
            raise ValueError(f"LLM returned invalid JSON: {e}") from e

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
            sources_json={"interview_id": interview_id},
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
