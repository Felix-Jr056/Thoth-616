# HOW TO ADD A NEW LLM TASK:
# 1. Create the prompt file at app/prompts/{task_name}.v1.md
#    Follow the format in app/prompts/EXAMPLE.v1.md
# 2. Add the task name, model, and max_tokens to TASK_MODEL_MAP below
# 3. Call it with: await llm.call("{task_name}", {"var": value})

from app.config import settings

TASK_MODEL_MAP: dict[str, tuple[str, int]] = {
    # --- Mini model: classification, judgment, follow-up generation ---
    "clarify_prompt":            (settings.LLM_MINI_MODEL, 200),
    "interview_topic":           (settings.LLM_MINI_MODEL, 300),
    "interview_refine_conclude": (settings.LLM_MINI_MODEL, 1500),
    "interview_followup":        (settings.LLM_MINI_MODEL, 300),
    "interview_planning":        (settings.LLM_MINI_MODEL, 500),

    # --- Full model: synthesis, answer generation, routing ---
    "synthesis_compose":         (settings.LLM_FULL_MODEL, 4000),
    "answer_generate":           (settings.LLM_FULL_MODEL, 1500),
    "sme_prompt":                (settings.LLM_FULL_MODEL, 500),
}


class ModelRouter:
    def get_model(self, task: str) -> str:
        if task not in TASK_MODEL_MAP:
            raise KeyError(
                f"Unknown LLM task '{task}'. "
                f"Register it in TASK_MODEL_MAP before use. "
                f"Known tasks: {sorted(TASK_MODEL_MAP.keys())}"
            )
        return TASK_MODEL_MAP[task][0]

    def get_max_tokens(self, task: str) -> int:
        return TASK_MODEL_MAP[task][1]
