from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from agentspec.adapters.base import AgentAdapter, AgentResponse, ToolCall

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"


@dataclass
class AdapterConfig:
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL))
    model: str = DEFAULT_MODEL
    max_tokens: int = 4096
    temperature: float = 0.0


class OpenAICompatibleAdapter(AgentAdapter):
    def __init__(self, config: AdapterConfig | None = None):
        self.config = config or AdapterConfig()
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> AgentResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        tools = self._build_tools()
        model_name = model or self.config.model

        start = time.monotonic()
        response = await self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools if tools else None,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        elapsed = time.monotonic() - start

        choice = response.choices[0]
        text = choice.message.content or ""

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    name=tc.function.name,
                    args=tc.function.arguments,
                ))

        token_usage = None
        if response.usage:
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return AgentResponse(
            text=text,
            tool_calls=tool_calls,
            latency_seconds=elapsed,
            token_usage=token_usage,
        )

    def _build_tools(self) -> list[dict]:
        return []
