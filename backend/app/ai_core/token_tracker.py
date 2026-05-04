import contextvars
from collections import defaultdict

_context: contextvars.ContextVar = contextvars.ContextVar("token_acc")


class TokenAccumulator:
    def __init__(self):
        self.by_model: dict[str, dict[str, int]] = defaultdict(
            lambda: {"prompt": 0, "completion": 0}
        )

    def add(self, model: str, prompt: int, completion: int) -> None:
        self.by_model[model]["prompt"] += prompt
        self.by_model[model]["completion"] += completion

    def to_usage_dict(self) -> dict | None:
        if not self.by_model:
            return None
        total_prompt = sum(v["prompt"] for v in self.by_model.values())
        total_completion = sum(v["completion"] for v in self.by_model.values())
        primary = max(
            self.by_model.items(),
            key=lambda kv: kv[1]["prompt"] + kv[1]["completion"],
        )[0]
        return {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "model": primary,
            "model_breakdown": [
                {
                    "model": m,
                    "prompt_tokens": v["prompt"],
                    "completion_tokens": v["completion"],
                }
                for m, v in self.by_model.items()
            ],
        }


class TokenTracker:
    @staticmethod
    def init() -> None:
        _context.set(TokenAccumulator())

    @staticmethod
    def record(model: str, prompt: int, completion: int) -> None:
        try:
            _context.get().add(model, prompt, completion)
        except LookupError:
            pass

    @staticmethod
    def collect() -> dict | None:
        try:
            return _context.get().to_usage_dict()
        except LookupError:
            return None
