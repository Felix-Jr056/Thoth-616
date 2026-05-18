from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.interview import Interview, InterviewTurn, InterviewTopicSummary
from app.schemas.interview import (
    InterviewRead, InterviewSummary, InterviewWithTurns, InterviewTurnRead
)
from app.repositories.utils import new_id


class InterviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        sme_id: str,
        topic: str,
        requested_by: str | None = None,
        admin_note: str | None = None,
        agenda: list[str] | None = None,
    ) -> InterviewRead:
        interview = Interview(
            id=new_id("int"),
            sme_id=sme_id,
            topic=topic,
            status="in_progress",
            requested_by=requested_by,
            admin_note=admin_note,
            agenda_json=agenda if agenda is not None else [topic],
            current_topic_index=0,
        )
        self.db.add(interview)
        await self.db.commit()
        await self.db.refresh(interview)
        return self._to_schema(interview)

    async def get(self, interview_id: str) -> InterviewRead | None:
        result = await self.db.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        return self._to_schema(interview) if interview else None

    async def list_by_sme(self, sme_id: str) -> list[InterviewSummary]:
        result = await self.db.execute(
            select(Interview)
            .where(Interview.sme_id == sme_id)
            .order_by(Interview.created_at.desc())
        )
        return [
            InterviewSummary(
                interview_id=i.id,
                topic=i.topic,
                status=i.status,
                created_at=i.created_at,
            )
            for i in result.scalars().all()
        ]

    async def get_with_turns(self, interview_id: str) -> InterviewWithTurns | None:
        result = await self.db.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            return None

        turns_result = await self.db.execute(
            select(InterviewTurn)
            .where(InterviewTurn.interview_id == interview_id)
            .order_by(InterviewTurn.turn_number.asc())
        )
        turns = [
            InterviewTurnRead(
                turn_number=t.turn_number,
                sme_response=t.sme_response,
                agent_follow_up=t.agent_follow_up,
                timestamp=t.created_at,
            )
            for t in turns_result.scalars().all()
        ]
        return InterviewWithTurns(
            interview_id=interview.id,
            sme_id=interview.sme_id,
            topic=interview.topic,
            status=interview.status,
            turns=turns,
        )

    async def add_turn(
        self,
        interview_id: str,
        sme_response: str,
        agent_follow_up: str | None,
        refined_summary: str | None = None,
    ):
        result = await self.db.execute(
            select(func.max(InterviewTurn.turn_number)).where(
                InterviewTurn.interview_id == interview_id
            )
        )
        max_turn = result.scalar() or 0
        turn = InterviewTurn(
            id=new_id("turn"),
            interview_id=interview_id,
            turn_number=max_turn + 1,
            sme_response=sme_response,
            agent_follow_up=agent_follow_up,
            refined_summary=refined_summary,
        )
        self.db.add(turn)
        await self.db.commit()
        await self.db.refresh(turn)
        return turn

    async def mark_completed(self, interview_id: str) -> None:
        result = await self.db.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        if interview:
            interview.status = "completed"
            await self.db.commit()

    async def save_topic_summary(
        self,
        interview_id: str,
        topic_index: int,
        topic_question: str,
        refined_content: str,
    ) -> None:
        # upsert: update existing row or insert a new summary for this topic
        existing = await self.db.execute(
            select(InterviewTopicSummary).where(
                InterviewTopicSummary.interview_id == interview_id,
                InterviewTopicSummary.topic_index == topic_index,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.topic_question = topic_question
            row.refined_content = refined_content
        else:
            summary = InterviewTopicSummary(
                id=new_id("tsum"),
                interview_id=interview_id,
                topic_index=topic_index,
                topic_question=topic_question,
                refined_content=refined_content,
            )
            self.db.add(summary)
        await self.db.commit()

    async def get_all_topic_summaries(self, interview_id: str) -> list[dict]:
        result = await self.db.execute(
            select(InterviewTopicSummary)
            .where(InterviewTopicSummary.interview_id == interview_id)
            .order_by(InterviewTopicSummary.topic_index.asc())
        )
        return [
            {
                "topic_index": s.topic_index,
                "topic_question": s.topic_question,
                "refined_content": s.refined_content,
            }
            for s in result.scalars().all()
        ]

    async def update_topic_index(self, interview_id: str, index: int) -> None:
        await self.db.execute(
            update(Interview)
            .where(Interview.id == interview_id)
            .values(current_topic_index=index)
        )
        await self.db.commit()

    async def get_agenda(self, interview_id: str) -> list[str]:
        result = await self.db.execute(
            select(Interview.agenda_json, Interview.current_topic_index)
            .where(Interview.id == interview_id)
        )
        row = result.one_or_none()
        if row is None:
            return []
        return row.agenda_json or []

    async def get_current_topic_index(self, interview_id: str) -> int:
        result = await self.db.execute(
            select(Interview.current_topic_index).where(Interview.id == interview_id)
        )
        row = result.scalar_one_or_none()
        return row if row is not None else 0

    async def set_topic_question(self, interview_id: str, question: str) -> None:
        await self.db.execute(
            update(Interview)
            .where(Interview.id == interview_id)
            .values(current_topic_question=question)
        )
        await self.db.commit()

    async def get_topic_question(self, interview_id: str) -> str | None:
        result = await self.db.execute(
            select(Interview.current_topic_question).where(Interview.id == interview_id)
        )
        return result.scalar_one_or_none()

    def _to_schema(self, interview: Interview) -> InterviewRead:
        return InterviewRead(
            interview_id=interview.id,
            sme_id=interview.sme_id,
            topic=interview.topic,
            status=interview.status,
            created_at=interview.created_at,
        )