from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class AgentResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    latency_seconds: float = 0.0
    token_usage: dict | None = None


class AgentAdapter(ABC):
    @abstractmethod
    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        fixtures: dict | None = None,
    ) -> AgentResponse:
        """Run the agent with the given prompt and return a response."""
