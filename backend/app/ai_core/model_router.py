# HOW TO ADD A NEW LLM TASK:
# 1. Create the prompt file at app/prompts/{task_name}.v1.md
#    Follow the format in app/prompts/EXAMPLE.v1.md
# 2. Add the task name and model to TASK_MODEL_MAP below
# 3. Call it with: await llm.call("{task_name}", {"var": value})

from app.config import settings

TASK_MODEL_MAP: dict[str, str] = {
    # --- Mini model: classification, judgment, follow-up generation ---
    "clarify_prompt":            settings.LLM_MINI_MODEL,
    "intent_classify":           settings.LLM_MINI_MODEL,
    "interview_topic":           settings.LLM_MINI_MODEL,
    "interview_refine":          settings.LLM_MINI_MODEL,
    "interview_conclude":        settings.LLM_MINI_MODEL,
    "interview_refine_conclude": settings.LLM_MINI_MODEL,
    "interview_followup":        settings.LLM_MINI_MODEL,
    "interview_planning":        settings.LLM_MINI_MODEL,

    # --- Full model: synthesis, answer generation, routing ---
    "synthesis_compose":         settings.LLM_FULL_MODEL,
    "answer_generate":           settings.LLM_FULL_MODEL,
    "sme_prompt":                settings.LLM_FULL_MODEL,
}


class ModelRouter:
    def get_model(self, task: str) -> str:
        if task not in TASK_MODEL_MAP:
            raise KeyError(
                f"Unknown LLM task '{task}'. "
                f"Register it in TASK_MODEL_MAP before use. "
                f"Known tasks: {sorted(TASK_MODEL_MAP.keys())}"
            )
        return TASK_MODEL_MAP[task]
