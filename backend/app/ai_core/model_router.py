TASK_MODEL_MAP: dict[str, str] = {
    # Fast/cheap — classification and path decisions
    "clarify_prompt":            "openai/gpt-4.1-mini",
    "intent_classify":           "openai/gpt-4.1-mini",
    "interview_followup":        "openai/gpt-4.1-mini",
    "fact_extraction_interview": "openai/gpt-4.1-mini",
    "fact_extraction_material":  "openai/gpt-4.1-mini",
    # Full — answer generation and SME routing
    "answer_generate":   "openai/gpt-4.1",
    "sme_prompt":        "openai/gpt-4.1",
    "synthesis_compose": "openai/gpt-4.1",
}


class ModelRouter:
    def get_model(self, task: str) -> str:
        return TASK_MODEL_MAP[task]  # raises KeyError for unknown tasks
