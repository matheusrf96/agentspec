from __future__ import annotations

import hashlib
import json
from collections.abc import MutableMapping

from agentspec.adapters.base import AgentAdapter, AgentResponse


class CachingAdapter(AgentAdapter):
    def __init__(
        self,
        inner: AgentAdapter,
        cache: MutableMapping | None = None,
    ):
        self.inner = inner
        self.cache = cache if cache is not None else {}

    def _make_key(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        fixtures: dict | None = None,
    ) -> str:
        raw = json.dumps(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": model,
                "fixtures": fixtures,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        fixtures: dict | None = None,
    ) -> AgentResponse:
        key = self._make_key(prompt, system_prompt, model, fixtures)
        if key in self.cache:
            cached = self.cache[key]
            return AgentResponse(
                text=cached.text,
                tool_calls=cached.tool_calls,
                latency_seconds=0.0,
                token_usage=cached.token_usage,
            )

        response = await self.inner.run(prompt, system_prompt, model, fixtures)
        self.cache[key] = response
        return response
