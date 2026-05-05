import json
import os
import re
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI
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
    def __init__(self, prompt_loader: PromptLoader, model_router: ModelRouter, client=None):
        self._prompts = prompt_loader
        self._router = model_router
        self._client = client or AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL") or None,
        )

    async def call(
        self,
        task: str,
        inputs: dict,
        response_format: Literal["text", "json"] = "text",
    ) -> LLMResponse:
        model = self._router.get_model(task)
        rendered = self._prompts.get(task, inputs)

        msg = await self._create(model=model, system=rendered.system, user=rendered.user)

        text = msg.choices[0].message.content
        TokenTracker.record(
            model=model,
            prompt=msg.usage.prompt_tokens,
            completion=msg.usage.completion_tokens,
        )

        parsed_json = None
        if response_format == "json":
            parsed_json = self._parse_json(text)

        return LLMResponse(text=text, json=parsed_json, model=model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4))
    async def _create(self, model: str, system: str, user: str):
        return await self._client.chat.completions.create(
            model=model,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
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
