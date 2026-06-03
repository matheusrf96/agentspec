from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentspec.adapters.openai_compatible_adapter import (
    AdapterConfig,
    OpenAICompatibleAdapter,
)


def _mock_choice(content: str = "Hello!", tool_calls: list | None = None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    return choice


def _mock_usage(
    prompt: int = 10,
    completion: int = 20,
    total: int = 30,
) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt
    usage.completion_tokens = completion
    usage.total_tokens = total
    return usage


def _mock_tool_call(
    name: str = "get_weather", args: str = '{"city": "London"}'
) -> MagicMock:
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = args
    return tc


def _mock_response(
    choices: list | None = None,
    usage: MagicMock | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.choices = choices or [_mock_choice()]
    resp.usage = usage or _mock_usage()
    return resp


@pytest.fixture
def adapter():
    config = AdapterConfig(
        api_key="sk-test", base_url="https://test.api.com", model="test-model"
    )
    return OpenAICompatibleAdapter(config)


class TestBasicResponse:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_returns_text(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("Hello world")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Say hi")
        assert response.text == "Hello world"
        assert response.latency_seconds >= 0

    @patch("openai.AsyncOpenAI")
    async def test_empty_content(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="")
        assert response.text == ""

    @patch("openai.AsyncOpenAI")
    async def test_no_tool_calls_by_default(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("Just text")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.tool_calls == []


class TestToolCalls:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_extracts_tool_calls(self, mock_openai, adapter):
        mock_client = AsyncMock()
        tool_calls = [_mock_tool_call("get_weather", '{"city": "London"}')]
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(
                choices=[_mock_choice("Getting weather", tool_calls=tool_calls)],
            )
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Weather?")
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"

    @patch("openai.AsyncOpenAI")
    async def test_multiple_tool_calls(self, mock_openai, adapter):
        mock_client = AsyncMock()
        tool_calls = [
            _mock_tool_call("tool1", '{"a": 1}'),
            _mock_tool_call("tool2", '{"b": 2}'),
        ]
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(
                choices=[_mock_choice("Running tools", tool_calls=tool_calls)],
            )
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Run tools")
        assert len(response.tool_calls) == 2


class TestTokenUsage:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_extracts_token_usage(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(
                choices=[_mock_choice("Done")],
                usage=_mock_usage(prompt=50, completion=100, total=150),
            )
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        expected = {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150}
        assert response.token_usage == expected

    @patch("openai.AsyncOpenAI")
    async def test_no_usage_when_none(self, mock_openai, adapter):
        mock_client = AsyncMock()
        resp = _mock_response(choices=[_mock_choice("Done")])
        resp.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=resp)
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.token_usage is None


class TestSystemPrompt:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_passes_system_prompt(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("OK")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi", system_prompt="Be helpful")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be helpful"}
        assert messages[1] == {"role": "user", "content": "Hi"}

    @patch("openai.AsyncOpenAI")
    async def test_no_system_prompt_when_none(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("OK")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hi"}


class TestModelOverride:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_uses_model_override(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("OK")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi", model="gpt-4")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"

    @patch("openai.AsyncOpenAI")
    async def test_uses_default_model(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("OK")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        await adapter.run(prompt="Hi")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "test-model"


class TestLatency:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_records_latency(self, mock_openai, adapter):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("Done")])
        )
        mock_openai.return_value = mock_client
        adapter.client = mock_client

        response = await adapter.run(prompt="Hi")
        assert response.latency_seconds > 0


class TestBuildTools:
    def test_build_tools_returns_empty_list(self, adapter):
        assert adapter._build_tools() == []


class TestConfig:
    def test_default_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-key")
        config = AdapterConfig()
        assert config.api_key == "sk-env-key"

    def test_default_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "https://custom.api.com")
        config = AdapterConfig()
        assert config.base_url == "https://custom.api.com"

    def test_default_base_url_fallback(self):
        config = AdapterConfig()
        assert config.base_url == "https://api.deepseek.com"

    def test_default_model(self):
        config = AdapterConfig()
        assert config.model == "deepseek-v4-pro"

    def test_explicit_config_override(self):
        config = AdapterConfig(
            api_key="sk-explicit",
            base_url="https://explicit.api.com",
            model="gpt-4o",
        )
        assert config.api_key == "sk-explicit"
        assert config.base_url == "https://explicit.api.com"
        assert config.model == "gpt-4o"
