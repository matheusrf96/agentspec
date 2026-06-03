from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from agentspec.adapters.base import AgentAdapter, AgentResponse, ToolCall

try:  # ruff: isort: skip
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    HumanMessage = None
    SystemMessage = None


@dataclass
class LangChainAdapterConfig:
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None
    config: dict[str, Any] | None = None


class LangChainAdapter(AgentAdapter):
    def __init__(
        self,
        runnable: Any,
        config: LangChainAdapterConfig | None = None,
    ):
        self.runnable = runnable
        self.config = config or LangChainAdapterConfig()

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> AgentResponse:
        messages: list = []
        if system_prompt and SystemMessage is not None:
            messages.append(SystemMessage(content=system_prompt))
        if HumanMessage is not None:
            messages.append(HumanMessage(content=prompt))

        kwargs: dict[str, Any] = {}
        resolved_model = model or self.config.model
        if resolved_model:
            kwargs["model"] = resolved_model

        run_config = self.config.config or {}
        start = time.monotonic()
        try:
            result = await self.runnable.ainvoke(messages, **run_config)
        except Exception:
            result = await self.runnable.ainvoke(
                {"messages": messages, **kwargs}, **run_config
            )
        elapsed = time.monotonic() - start

        return _parse_output(result, elapsed)


def _parse_output(result: Any, elapsed: float) -> AgentResponse:
    text: str = ""
    tool_calls: list[ToolCall] = []
    token_usage: dict | None = None

    if isinstance(result, dict):
        content = result.get("content") or result.get("output") or ""
        text = str(content)
        for tc in result.get("tool_calls", []):
            if isinstance(tc, dict):
                tool_calls.append(
                    ToolCall(
                        name=str(tc.get("name", "")),
                        args=tc.get("args", {}),
                    )
                )
    elif hasattr(result, "content"):
        text = str(result.content or "")
        if hasattr(result, "tool_calls") and result.tool_calls:
            for tc in result.tool_calls:
                if isinstance(tc, dict):
                    tool_calls.append(
                        ToolCall(
                            name=str(tc.get("name", "")),
                            args=tc.get("args", {}),
                        )
                    )
        if hasattr(result, "usage_metadata") and result.usage_metadata:
            um = result.usage_metadata
            token_usage = {
                "prompt_tokens": (
                    getattr(um, "input_tokens", 0) or um.get("input_tokens", 0)
                ),
                "completion_tokens": (
                    getattr(um, "output_tokens", 0) or um.get("output_tokens", 0)
                ),
                "total_tokens": (
                    getattr(um, "total_tokens", 0) or um.get("total_tokens", 0)
                ),
            }
    else:
        text = str(result)

    return AgentResponse(
        text=text,
        tool_calls=tool_calls,
        latency_seconds=elapsed,
        token_usage=token_usage,
    )
