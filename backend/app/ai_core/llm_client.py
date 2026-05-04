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

    @property
    def content(self) -> str:
        """Alias for .text — lets C's InterviewService/SynthesisService use this client unchanged."""
        return self.text


class LLMClient:
    def __init__(self, prompt_loader: PromptLoader | None = None, model_router: ModelRouter | None = None, client=None):
        self._prompts = prompt_loader
        self._router = model_router
        self._client = client or AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL") or None,
        )
        # Model names used by C's interview/synthesis services
        self.interview_model = os.getenv("INTERVIEW_MODEL", "openai/gpt-4.1-mini")
        self.synthesis_model = os.getenv("SYNTHESIS_MODEL", "openai/gpt-4.1")
        self.planning_model = os.getenv("PLANNING_MODEL", "openai/gpt-4.1")

    # ── D's task-based interface (requires PromptLoader + ModelRouter) ─────

    async def call(
        self,
        task: str,
        inputs: dict,
        response_format: Literal["text", "json"] = "text",
    ) -> LLMResponse:
        if self._prompts is None or self._router is None:
            raise ValueError("LLMClient.call() requires prompt_loader and model_router")
        model = self._router.get_model(task)
        rendered = self._prompts.get(task, inputs)
        msg = await self._create(model=model, system=rendered.system, user=rendered.user)
        text = msg.choices[0].message.content
        TokenTracker.record(model=model, prompt=msg.usage.prompt_tokens, completion=msg.usage.completion_tokens)
        parsed_json = self._parse_json(text) if response_format == "json" else None
        return LLMResponse(text=text, json=parsed_json, model=model)

    # ── C's raw-messages interface (used by InterviewService, SynthesisService) ──

    async def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        msg = await self._chat_create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        text = msg.choices[0].message.content
        TokenTracker.record(model=model, prompt=msg.usage.prompt_tokens, completion=msg.usage.completion_tokens)
        return LLMResponse(text=text, json=None, model=model)

    # ── Internal helpers ────────────────────────────────────────────────────

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4))
    async def _chat_create(self, model: str, messages: list[dict], temperature: float, max_tokens: int):
        return await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
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
