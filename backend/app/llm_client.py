import os
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


@dataclass
class LLMResponse:
    content: str
    usage: dict


class LLMClient:
    def __init__(self):
        self.interview_model = os.getenv("INTERVIEW_MODEL", "gpt-4o-mini")
        self.synthesis_model = os.getenv("SYNTHESIS_MODEL", "gpt-4o")
        self.planning_model = os.getenv("PLANNING_MODEL", "openai/gpt-4.1")
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL") or None
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        )
