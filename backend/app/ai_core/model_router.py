TASK_MODEL_MAP: dict[str, str] = {
    # Haiku — classification and path decisions
    "clarify_prompt":            "claude-haiku-4-5-20251001",
    "intent_classify":           "claude-haiku-4-5-20251001",  # kept for backward compat
    "interview_followup":        "claude-haiku-4-5-20251001",
    "fact_extraction_interview": "claude-haiku-4-5-20251001",
    "fact_extraction_material":  "claude-haiku-4-5-20251001",
    # Sonnet — answer generation and SME routing
    "answer_generate":   "claude-sonnet-4-6",
    "sme_prompt":        "claude-sonnet-4-6",
    "synthesis_compose": "claude-sonnet-4-6",
}


class ModelRouter:
    def get_model(self, task: str) -> str:
        return TASK_MODEL_MAP[task]  # raises KeyError for unknown tasks
