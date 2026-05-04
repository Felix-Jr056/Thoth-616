import uuid
from datetime import datetime, timezone


class InterviewRepository:
    def __init__(self):
        self._interviews: dict = {}
        self._turns: dict[str, list] = {}
        self._topic_summaries: dict[str, list] = {}

    async def create(
        self,
        sme_id: str,
        topic: str,
        requested_by: str = "sme",
        admin_note: str = "",
    ) -> dict:
        interview_id = str(uuid.uuid4())
        interview = {
            "id": interview_id,
            "sme_id": sme_id,
            "topic": topic,
            "status": "in_progress",
            "requested_by": requested_by,
            "admin_note": admin_note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._interviews[interview_id] = interview
        self._turns[interview_id] = []
        self._topic_summaries[interview_id] = []
        return interview

    async def get_with_turns(self, interview_id: str) -> dict | None:
        interview = self._interviews.get(interview_id)
        if interview is None:
            return None
        return {
            "interview": interview,
            "turns": list(self._turns.get(interview_id, [])),
        }

    async def add_turn(
        self,
        interview_id: str,
        sme_response: str,
        agent_follow_up: str | None,
        refined_summary: str,
    ) -> dict:
        turns = self._turns.setdefault(interview_id, [])
        turn = {
            "turn_number": len(turns) + 1,
            "sme_response": sme_response,
            "agent_follow_up": agent_follow_up,
            "refined_summary": refined_summary,
        }
        turns.append(turn)
        return turn

    async def mark_completed(self, interview_id: str) -> None:
        if interview_id in self._interviews:
            self._interviews[interview_id]["status"] = "completed"

    async def save_topic_summary(
        self,
        interview_id: str,
        topic_index: int,
        topic_question: str,
        refined_content: str,
    ) -> None:
        summaries = self._topic_summaries.setdefault(interview_id, [])
        for entry in summaries:
            if entry["topic_index"] == topic_index:
                entry["refined_content"] = refined_content
                return
        summaries.append({
            "topic_index": topic_index,
            "topic_question": topic_question,
            "refined_content": refined_content,
        })

    async def get_all_topic_summaries(self, interview_id: str) -> list[dict]:
        summaries = self._topic_summaries.get(interview_id, [])
        return sorted(summaries, key=lambda s: s["topic_index"])


class KnowledgeEntryRepository:
    def __init__(self):
        self._entries: dict = {}

    async def create(
        self,
        sme_id: str,
        topic: str,
        content: str,
        sources_json: dict,
        source_interview_id: str = "",
    ) -> dict:
        entry_id = str(uuid.uuid4())
        entry = {
            "id": entry_id,
            "sme_id": sme_id,
            "topic": topic,
            "content": content,
            "sources_json": sources_json,
            "source_interview_id": source_interview_id,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._entries[entry_id] = entry
        return entry

    async def get(self, entry_id: str) -> dict | None:
        return self._entries.get(entry_id)

    async def update_status(
        self,
        entry_id: str,
        status: str,
        rejection_reason: str | None = None,
    ) -> None:
        if entry_id in self._entries:
            self._entries[entry_id]["status"] = status
            if rejection_reason is not None:
                self._entries[entry_id]["rejection_reason"] = rejection_reason
