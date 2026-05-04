import json
import re
from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai_core.prompt_loader import PromptLoader
from app.ai_core.model_router import ModelRouter
from app.ai_core.token_tracker import TokenTracker


@dataclass
class LLMResponse:
    text: str
    json: dict | None
    model: str


class LLMClient:
    def __init__(self, prompt_loader: PromptLoader, model_router: ModelRouter):
        self._prompts = prompt_loader
        self._router = model_router
        self._client = AsyncAnthropic()

    async def call(
        self,
        task: str,
        inputs: dict,
        response_format: Literal["text", "json"] = "text",
    ) -> LLMResponse:
        model = self._router.get_model(task)
        rendered = self._prompts.get(task, inputs)

        msg = await self._create(model=model, system=rendered.system, user=rendered.user)

        text = msg.content[0].text
        TokenTracker.record(
            model=model,
            prompt=msg.usage.input_tokens,
            completion=msg.usage.output_tokens,
        )

        parsed_json = None
        if response_format == "json":
            parsed_json = self._parse_json(text)

        return LLMResponse(text=text, json=parsed_json, model=model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4))
    async def _create(self, model: str, system: str, user: str):
        return await self._client.messages.create(
            model=model,
            max_tokens=4000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
