import os

from app.llm_client import LLMClient
from app.repositories.stub import InterviewRepository, KnowledgeEntryRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService

# Module-level singletons so C's routes share the same in-memory state.
interview_repo = InterviewRepository()
knowledge_repo = KnowledgeEntryRepository()
os.environ.setdefault("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "sk-local-placeholder"))
llm = LLMClient()

interview_service = InterviewService(interview_repo=interview_repo, llm=llm)
synthesis_service = SynthesisService(
    interview_repo=interview_repo,
    knowledge_repo=knowledge_repo,
    llm=llm,
)
