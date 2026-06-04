from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentspec.adapters.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicAdapterConfig,
)


def _mock_text_block(text: str = "Hello from Claude") -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _mock_tool_use_block(
    name: str = "get_weather",
    input_data: dict | None = None,
) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data or {"city": "London"}
    return block


def _mock_usage(input_tokens: int = 10, output_tokens: int = 20) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    return usage


def _mock_response(
    content: list | None = None,
    usage: MagicMock | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.content = content or [_mock_text_block()]
    resp.usage = usage or _mock_usage()
    return resp


@pytest.fixture
def adapter():
    config = AnthropicAdapterConfig(
        api_key="sk-ant-test", model="claude-sonnet-4-20250514"
    )
    return AnthropicAdapter(config)


class TestAnthropicDefaults:
    def test_default_model(self):
        adapter = AnthropicAdapter(AnthropicAdapterConfig(api_key="sk-test"))
        assert adapter.config.model == "claude-sonnet-4-20250514"

    def test_env_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
        adapter = AnthropicAdapter()
        assert adapter.config.api_key == "sk-ant-env"


class TestAnthropicRun:
    pytestmark = pytest.mark.asyncio

    @patch("anthropic.AsyncAnthropic")
    async def test_returns_text(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("Hello from Claude")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Say hi")
        assert response.text == "Hello from Claude"
        assert response.latency_seconds >= 0

    @patch("anthropic.AsyncAnthropic")
    async def test_returns_empty_text(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="")
        assert response.text == ""

    @patch("anthropic.AsyncAnthropic")
    async def test_no_tool_calls_by_default(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("Just text")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.tool_calls == []

    @patch("anthropic.AsyncAnthropic")
    async def test_extracts_tool_calls(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(
                content=[
                    _mock_text_block("Getting weather"),
                    _mock_tool_use_block("get_weather", {"city": "London"}),
                ]
            )
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Weather?")
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"

    @patch("anthropic.AsyncAnthropic")
    async def test_multiple_tool_calls(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(
                content=[
                    _mock_text_block("Running tools"),
                    _mock_tool_use_block("tool1", {"a": 1}),
                    _mock_tool_use_block("tool2", {"b": 2}),
                ]
            )
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Run tools")
        assert len(response.tool_calls) == 2


class TestAnthropicTokenUsage:
    pytestmark = pytest.mark.asyncio

    @patch("anthropic.AsyncAnthropic")
    async def test_extracts_token_usage(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(
                content=[_mock_text_block("Done")],
                usage=_mock_usage(input_tokens=50, output_tokens=100),
            )
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.token_usage == {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        }

    @patch("anthropic.AsyncAnthropic")
    async def test_no_usage_when_none(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        resp = _mock_response(content=[_mock_text_block("Done")])
        resp.usage = None
        mock_client.messages.create = AsyncMock(return_value=resp)
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.token_usage is None


class TestAnthropicSystemPrompt:
    pytestmark = pytest.mark.asyncio

    @patch("anthropic.AsyncAnthropic")
    async def test_passes_system_prompt(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("OK")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi", system_prompt="Be helpful")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be helpful"
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]

    @patch("anthropic.AsyncAnthropic")
    async def test_no_system_prompt_when_none(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("OK")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


class TestAnthropicModelOverride:
    pytestmark = pytest.mark.asyncio

    @patch("anthropic.AsyncAnthropic")
    async def test_uses_model_override(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("OK")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi", model="claude-3-opus-20240229")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus-20240229"

    @patch("anthropic.AsyncAnthropic")
    async def test_uses_default_model(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("OK")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi")
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"


class TestAnthropicLatency:
    pytestmark = pytest.mark.asyncio

    @patch("anthropic.AsyncAnthropic")
    async def test_records_latency(self, mock_anthropic, adapter):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(content=[_mock_text_block("Done")])
        )
        mock_anthropic.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.latency_seconds > 0


class TestAnthropicBuildTools:
    def test_build_tools_returns_empty_list(self, adapter):
        assert adapter._build_tools() == []


class TestAnthropicNoDependency:
    def test_raises_when_anthropic_not_installed(self):
        import importlib

        mod = importlib.import_module("agentspec.adapters.anthropic_adapter")
        with patch.object(mod, "AsyncAnthropic", None):
            with pytest.raises(ImportError, match="anthropic package is required"):
                mod.AnthropicAdapter()
