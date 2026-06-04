from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentspec.adapters.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicAdapterConfig,
)


def _make_response(text: str = "reply") -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text=text)]
    resp.usage = MagicMock(input_tokens=10, output_tokens=5)
    return resp


class TestAnthropicFixtures:
    pytestmark = pytest.mark.asyncio

    async def test_conversation_history(self):
        adapter = AnthropicAdapter(AnthropicAdapterConfig(api_key="sk-test"))
        adapter.client = AsyncMock()
        adapter.client.messages.create = AsyncMock(return_value=_make_response("reply"))

        response = await adapter.run(
            prompt="final",
            fixtures={
                "conversation_history": [
                    {"role": "user", "content": "first msg"},
                    {"role": "assistant", "content": "first reply"},
                ]
            },
        )
        call_kwargs = adapter.client.messages.create.call_args[1]
        assert call_kwargs["messages"] == [
            {"role": "user", "content": "first msg"},
            {"role": "assistant", "content": "first reply"},
            {"role": "user", "content": "final"},
        ]
        assert response.text == "reply"

    async def test_canned_response(self):
        adapter = AnthropicAdapter(AnthropicAdapterConfig(api_key="sk-test"))
        adapter.client = AsyncMock()

        response = await adapter.run(
            prompt="trigger word",
            fixtures={
                "canned_responses": [
                    {"prompt_contains": "trigger", "output": "canned reply"}
                ]
            },
        )
        assert response.text == "canned reply"
        assert response.latency_seconds == 0.0
        adapter.client.messages.create.assert_not_called()

    async def test_canned_response_with_tool_calls(self):
        adapter = AnthropicAdapter(AnthropicAdapterConfig(api_key="sk-test"))
        adapter.client = AsyncMock()

        response = await adapter.run(
            prompt="trigger word",
            fixtures={
                "canned_responses": [
                    {
                        "prompt_contains": "trigger",
                        "output": "tool result",
                        "tool_calls": [
                            {"name": "get_weather", "args": {"city": "London"}},
                        ],
                    }
                ]
            },
        )
        assert response.text == "tool result"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"

    async def test_build_tools_with_mock_tools(self):
        adapter = AnthropicAdapter(AnthropicAdapterConfig(api_key="sk-test"))
        adapter.client = AsyncMock()
        adapter.client.messages.create = AsyncMock(
            return_value=_make_response("using tool")
        )

        await adapter.run(
            prompt="use tool",
            fixtures={
                "mock_tools": [
                    {"name": "get_weather", "description": "Get the weather"}
                ]
            },
        )
        call_kwargs = adapter.client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == [
            {
                "name": "get_weather",
                "description": "Get the weather",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]


class TestAnthropicImportError:
    def test_exception_block(self):
        import importlib

        mod = importlib.import_module("agentspec.adapters.anthropic_adapter")
        with patch.object(mod, "AsyncAnthropic", None):
            with pytest.raises(ImportError, match="anthropic package is required"):
                mod.AnthropicAdapter()
