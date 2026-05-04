import logging
import re
from pathlib import Path

from app.ai_core.llm_client import LLMClient
from app.repositories.stub import InterviewRepository

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


class InterviewService:
    def __init__(self, interview_repo: InterviewRepository, llm: LLMClient):
        self._repo = interview_repo
        self._llm = llm
        # Transient state per interview — mirrors what a real repo would persist.
        # Lost on restart (same as the in-memory stub), which is fine for dev.
        self._state: dict[str, dict] = {}

    # ------------------------------------------------------------------ public

    async def generate_agenda(
        self,
        sme_profile: dict,
        unanswered_questions: list[str],
        uploaded_materials: str,
    ) -> list[str]:
        """Call planning_model to produce a list of knowledge-gap topic statements."""
        template = _load_prompt("interview_planning.md")

        profile_str = "\n".join(f"- {k}: {v}" for k, v in sme_profile.items())
        questions_str = (
            "\n".join(f"- {q}" for q in unanswered_questions)
            if unanswered_questions else "None"
        )
        recorded = sme_profile.get("recorded_topics", [])
        recorded_str = "\n".join(f"- {t}" for t in recorded) if recorded else "None"

        prompt = (
            template
            .replace("{sme_profile}", profile_str)
            .replace("{unanswered_questions}", questions_str)
            .replace("{uploaded_materials}", uploaded_materials or "None")
            .replace("{recorded_topics}", recorded_str)
        )

        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.planning_model,
            temperature=0.3,
            max_tokens=2000,
        )

        topics = []
        for line in response.content.strip().splitlines():
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            if cleaned:
                topics.append(cleaned)
        return topics

    async def create_interview(
        self,
        sme_id: str,
        name: str,
        role: str,
        department: str,
        specialization: str,
        responsible_products: list[str],
        sub_expertise: list[str],
        recorded_topics: list[str],
        agenda: list[str],
        requested_by: str = "sme",
        admin_note: str = "",
    ) -> dict:
        interview = await self._repo.create(
            sme_id=sme_id,
            topic=specialization,
            requested_by=requested_by,
            admin_note=admin_note,
        )
        interview_id = interview["id"]

        sme_profile = {
            "name": name,
            "role": role,
            "department": department,
            "specialization": specialization,
            "responsible_products": responsible_products,
            "sub_expertise": sub_expertise,
            "recorded_topics": recorded_topics,
        }

        agenda_item_0 = agenda[0] if agenda else specialization
        first_question = await self._generate_topic_question(
            agenda_item=agenda_item_0,
            sme_profile=sme_profile,
        )

        self._state[interview_id] = {
            "sme_profile": sme_profile,
            "agenda": agenda,
            "specialization": specialization,
            "topic_index": 0,
            "topic_question": first_question,
            "turn_count": 0,
            "refined_summary": "",
            "prev_topic_index": None,
            "prev_topic_question": None,
            "completed": False,
        }

        return {
            "interview_id": interview_id,
            "first_question": first_question,
            "topic_index": 0,
            "total_topics": len(agenda),
        }

    async def submit_answer(self, interview_id: str, sme_response: str) -> dict:
        if self._state.get(interview_id, {}).get("completed"):
            return {"type": "completed", "interview_id": interview_id}

        data = await self._repo.get_with_turns(interview_id)
        if data is None:
            return None

        state = self._state.get(interview_id) or await self._reconstruct_state(interview_id, data)

        topic_question = state["topic_question"]
        turn_count = state["turn_count"]

        # Refine: only current-topic context passes through (isolation guaranteed by
        # state["refined_summary"] which resets to "" at the start of every topic).
        refined_summary = await self._refine_topic(
            topic_question=topic_question,
            previous_summary=state["refined_summary"],
            sme_response=sme_response,
        )

        new_turn_count = turn_count + 1

        agenda = state.get("agenda", [])
        total_topics = len(agenda) if agenda else 10

        # Decide: continue asking or conclude this topic
        if new_turn_count >= 10:
            decision = "CONCLUDE"
        else:
            decision = await self._conclude_or_continue(
                topic_question=topic_question,
                refined_summary=refined_summary,
                turn_number=new_turn_count,
            )

        if decision == "CONTINUE":
            follow_up = await self._generate_followup(refined_summary)
            await self._repo.add_turn(
                interview_id=interview_id,
                sme_response=sme_response,
                agent_follow_up=follow_up,
                refined_summary=refined_summary,
            )
            state["turn_count"] = new_turn_count
            state["refined_summary"] = refined_summary
            return {
                "type": "followup",
                "question": follow_up,
                "turn_number": new_turn_count,
                "topic_index": state["topic_index"],
                "interview_id": interview_id,
            }

        # CONCLUDE branch
        await self._repo.add_turn(
            interview_id=interview_id,
            sme_response=sme_response,
            agent_follow_up=None,
            refined_summary=refined_summary,
        )
        topic_index = state["topic_index"]
        await self._repo.save_topic_summary(
            interview_id=interview_id,
            topic_index=topic_index,
            topic_question=topic_question,
            refined_content=refined_summary,
        )

        state["refined_summary"] = refined_summary  # keep for complete_topic fallback
        state["prev_topic_index"] = topic_index
        state["prev_topic_question"] = topic_question
        next_topic_index = topic_index + 1

        if next_topic_index < total_topics:
            agenda_item = agenda[next_topic_index] if agenda else f"topic {next_topic_index + 1}"
            next_question = await self._generate_topic_question(
                agenda_item=agenda_item,
                sme_profile=state["sme_profile"],
            )
            state["topic_index"] = next_topic_index
            state["topic_question"] = next_question
            state["turn_count"] = 0
            state["refined_summary"] = ""
            return {
                "type": "next_topic",
                "question": next_question,
                "topic_index": next_topic_index,
                "total_topics": total_topics,
            }

        await self._repo.mark_completed(interview_id)
        state["completed"] = True
        return {"type": "completed", "interview_id": interview_id}

    async def add_supplement(self, interview_id: str, supplement: str) -> dict:
        data = await self._repo.get_with_turns(interview_id)
        if data is None:
            raise ValueError(f"Interview {interview_id} not found")

        state = self._state.get(interview_id) or await self._reconstruct_state(interview_id, data)

        prev_idx = state.get("prev_topic_index")
        if prev_idx is None:
            raise ValueError("No concluded topic to supplement")

        summaries = await self._repo.get_all_topic_summaries(interview_id)
        prev_summary = next((s for s in summaries if s["topic_index"] == prev_idx), None)
        if prev_summary is None:
            raise ValueError(f"No summary found for topic {prev_idx}")

        updated_content = prev_summary["refined_content"] + "\n\nSupplement: " + supplement
        await self._repo.save_topic_summary(
            interview_id=interview_id,
            topic_index=prev_idx,
            topic_question=prev_summary["topic_question"],
            refined_content=updated_content,
        )

        if state.get("completed"):
            return {"type": "completed", "interview_id": interview_id}

        return {
            "type": "next_topic",
            "question": state["topic_question"],
            "topic_index": state["topic_index"],
        }

    async def complete_topic(self, interview_id: str) -> dict:
        """Explicitly mark the current topic complete and save its refined content."""
        state = self._state.get(interview_id)
        if state is None:
            raise ValueError(f"Interview {interview_id} not in session")

        topic_index = state["topic_index"]
        agenda = state.get("agenda", [])
        total_topics = len(agenda) if agenda else 10

        await self._repo.save_topic_summary(
            interview_id=interview_id,
            topic_index=topic_index,
            topic_question=state["topic_question"],
            refined_content=state["refined_summary"],
        )

        state["prev_topic_index"] = topic_index
        state["prev_topic_question"] = state["topic_question"]

        remaining = total_topics - topic_index - 1
        return {
            "completed_topic_index": topic_index,
            "total_topics": total_topics,
            "remaining": remaining,
        }

    async def get_next_topic(self, interview_id: str) -> dict:
        """Advance to the next agenda topic and return its question."""
        state = self._state.get(interview_id)
        if state is None:
            raise ValueError(f"Interview {interview_id} not in session")

        agenda = state.get("agenda", [])
        total_topics = len(agenda) if agenda else 10
        next_topic_index = state["topic_index"] + 1

        if next_topic_index >= total_topics:
            await self._repo.mark_completed(interview_id)
            state["completed"] = True
            return {"type": "completed"}

        agenda_item = agenda[next_topic_index] if agenda else f"topic {next_topic_index + 1}"
        next_question = await self._generate_topic_question(
            agenda_item=agenda_item,
            sme_profile=state["sme_profile"],
        )

        state["topic_index"] = next_topic_index
        state["topic_question"] = next_question
        state["turn_count"] = 0
        state["refined_summary"] = ""

        return {
            "type": "next_topic",
            "question": next_question,
            "topic_index": next_topic_index,
            "total_topics": total_topics,
        }

    async def resume_interview(self, interview_id: str) -> dict:
        state = self._state.get(interview_id)
        if state is None:
            data = await self._repo.get_with_turns(interview_id)
            if data is None:
                raise ValueError(f"Interview {interview_id} not found")
            state = await self._reconstruct_state(interview_id, data)

        return {
            "topic_index": state["topic_index"],
            "turn_number": state["turn_count"],
            "last_question": state["topic_question"],
        }

    # ------------------------------------------------------------------ helpers

    async def _reconstruct_state(self, interview_id: str, data: dict) -> dict:
        """Best-effort reconstruction after a service restart (in-memory state lost)."""
        summaries = await self._repo.get_all_topic_summaries(interview_id)
        topic_index = len(summaries)
        specialization = data["interview"].get("topic", "")

        topic_question = "Please continue — what else can you share on this topic?"
        refined_summary = ""
        prev_topic_index = None
        prev_topic_question = None

        if summaries:
            last = summaries[-1]
            refined_summary = last.get("refined_content", "")
            prev_topic_index = last["topic_index"]
            prev_topic_question = last["topic_question"]

        state = {
            "sme_profile": {
                "name": "", "role": "", "department": "",
                "specialization": specialization,
                "responsible_products": [], "sub_expertise": [], "recorded_topics": [],
            },
            "agenda": [],
            "specialization": specialization,
            "topic_index": topic_index,
            "topic_question": topic_question,
            "turn_count": 0,
            "refined_summary": refined_summary,
            "prev_topic_index": prev_topic_index,
            "prev_topic_question": prev_topic_question,
            "completed": data["interview"].get("status") == "completed",
        }
        self._state[interview_id] = state
        return state

    async def _generate_topic_question(self, agenda_item: str, sme_profile: dict) -> str:
        template = _load_prompt("interview_topic.md")
        prompt = (
            template
            .replace("{sme_name}", sme_profile.get("name", ""))
            .replace("{sme_role}", sme_profile.get("role", ""))
            .replace("{sme_department}", sme_profile.get("department", ""))
            .replace("{sme_responsible_products}", ", ".join(sme_profile.get("responsible_products", [])))
            .replace("{sme_sub_expertise}", ", ".join(sme_profile.get("sub_expertise", [])))
            .replace("{agenda_item}", agenda_item)
        )
        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.interview_model,
            temperature=0.5,
        )
        return response.content.strip()

    async def _refine_topic(
        self, topic_question: str, previous_summary: str, sme_response: str
    ) -> str:
        template = _load_prompt("interview_refine.md")
        prompt = (
            template
            .replace("{topic_question}", topic_question)
            .replace("{previous_summary}", previous_summary or "(none yet)")
            .replace("{sme_response}", sme_response)
        )
        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.interview_model,
        )
        return response.content.strip()

    async def _conclude_or_continue(
        self, topic_question: str, refined_summary: str, turn_number: int
    ) -> str:
        template = _load_prompt("interview_conclude.md")
        prompt = (
            template
            .replace("{topic_question}", topic_question)
            .replace("{refined_summary}", refined_summary)
            .replace("{turn_number}", str(turn_number))
        )
        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.interview_model,
            max_tokens=16,
        )
        result = response.content.strip().upper()
        return "CONTINUE" if "CONTINUE" in result else "CONCLUDE"

    async def _generate_followup(self, refined_summary: str) -> str:
        template = _load_prompt("interview_followup.md")
        prompt = template.replace("{refined_summary}", refined_summary)
        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self._llm.interview_model,
        )
        return response.content.strip()
