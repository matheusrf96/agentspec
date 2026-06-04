from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentspec.adapters.base import AgentAdapter, AgentResponse
from agentspec.adapters.caching_adapter import CachingAdapter


class _CountingAdapter(AgentAdapter):
    def __init__(self):
        self.run_count = 0

    async def run(self, prompt, system_prompt=None, model=None, fixtures=None):
        self.run_count += 1
        return AgentResponse(text=f"Echo: {prompt}")


class TestCachingAdapter:
    pytestmark = pytest.mark.asyncio

    async def test_caches_response(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)

        r1 = await adapter.run(prompt="hello")
        r2 = await adapter.run(prompt="hello")

        assert r1.text == r2.text
        assert inner.run_count == 1

    async def test_cache_miss_on_different_prompt(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)

        await adapter.run(prompt="hello")
        await adapter.run(prompt="world")

        assert inner.run_count == 2

    async def test_cache_key_includes_system_prompt(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)

        await adapter.run(prompt="hello", system_prompt="be helpful")
        await adapter.run(prompt="hello", system_prompt="be mean")

        assert inner.run_count == 2

    async def test_cache_key_includes_model(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)

        await adapter.run(prompt="hello", model="gpt-4")
        await adapter.run(prompt="hello", model="claude-3")

        assert inner.run_count == 2

    async def test_cached_response_has_zero_latency(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)
        await adapter.run(prompt="hello")

        response = await adapter.run(prompt="hello")
        assert response.latency_seconds == 0.0

    async def test_caches_tool_calls(self):
        inner = AsyncMock(spec=AgentAdapter)
        inner.run.return_value = AgentResponse(
            text="ok",
            tool_calls=[MagicMock()],
        )
        adapter = CachingAdapter(inner)

        r1 = await adapter.run(prompt="tools")
        r2 = await adapter.run(prompt="tools")

        assert len(r2.tool_calls) == len(r1.tool_calls)

    async def test_uses_provided_cache_dict(self):
        shared = {}
        inner = _CountingAdapter()
        adapter1 = CachingAdapter(inner, cache=shared)
        adapter2 = CachingAdapter(inner, cache=shared)

        await adapter1.run(prompt="shared")
        await adapter2.run(prompt="shared")

        assert inner.run_count == 1

    async def test_caches_token_usage(self):
        inner = _CountingAdapter()
        adapter = CachingAdapter(inner)

        response = await adapter.run(prompt="hello")
        response.token_usage = {"total_tokens": 42}

        cached = await adapter.run(prompt="hello")
        assert cached.token_usage == {"total_tokens": 42}
