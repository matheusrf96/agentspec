from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from agentspec.adapters.base import AgentAdapter, AgentResponse, ToolCall

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore[assignment,misc]


@dataclass
class AnthropicAdapterConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.0


class AnthropicAdapter(AgentAdapter):
    def __init__(self, config: AnthropicAdapterConfig | None = None):
        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package is required. pip install agentspec[anthropic]"
            )
        self.config = config or AnthropicAdapterConfig()
        self.client = AsyncAnthropic(api_key=self.config.api_key)

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        fixtures: dict | None = None,
    ) -> AgentResponse:
        system = system_prompt
        messages: list[dict] = []

        if fixtures:
            history = fixtures.get("conversation_history", [])
            for entry in history:
                messages.append({"role": entry["role"], "content": entry["content"]})

            canned = fixtures.get("canned_responses", [])
            for cr in canned:
                if cr["prompt_contains"] in prompt:
                    return AgentResponse(
                        text=cr.get("output", ""),
                        tool_calls=[
                            ToolCall(**tc) for tc in (cr.get("tool_calls") or [])
                        ],
                        latency_seconds=0.0,
                    )

        messages.append({"role": "user", "content": prompt})

        model_name = model or self.config.model
        api_tools = self._build_tools(fixtures)

        create_kwargs: dict = {
            "model": model_name,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": messages,  # type: ignore[arg-type]
        }
        if system:
            create_kwargs["system"] = system
        if api_tools:
            create_kwargs["tools"] = api_tools  # type: ignore[arg-type]

        start = time.monotonic()
        response = await self.client.messages.create(**create_kwargs)
        elapsed = time.monotonic() - start

        text = ""
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        name=block.name,
                        args=dict(block.input),
                    )
                )

        token_usage = None
        if response.usage:
            token_usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            }

        return AgentResponse(
            text=text,
            tool_calls=tool_calls,
            latency_seconds=elapsed,
            token_usage=token_usage,
        )

    def _build_tools(  # type: ignore[return]
        self, fixtures: dict | None = None
    ) -> list[dict]:
        tools = []
        if fixtures:
            for mt in fixtures.get("mock_tools", []):
                tools.append(
                    {
                        "name": mt["name"],
                        "description": mt.get("description", ""),
                        "input_schema": {
                            "type": "object",
                            "properties": {},
                        },
                    }
                )
        return tools
