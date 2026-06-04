from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentspec.adapters.ollama_adapter import (
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OllamaAdapter,
)
from agentspec.adapters.openai_compatible_adapter import AdapterConfig


def _mock_choice(content: str = "Hello!") -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    return choice


def _mock_usage(prompt: int = 10, completion: int = 20, total: int = 30) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt
    usage.completion_tokens = completion
    usage.total_tokens = total
    return usage


def _mock_response(
    choices: list | None = None, usage: MagicMock | None = None
) -> MagicMock:
    resp = MagicMock()
    resp.choices = choices or [_mock_choice()]
    resp.usage = usage or _mock_usage()
    return resp


class TestOllamaDefaults:
    def test_default_base_url(self):
        adapter = OllamaAdapter()
        assert adapter.config.base_url == OLLAMA_BASE_URL

    def test_default_model(self):
        adapter = OllamaAdapter()
        assert adapter.config.model == OLLAMA_DEFAULT_MODEL

    def test_env_override_base_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434/v1")
        adapter = OllamaAdapter()
        assert adapter.config.base_url == "http://custom:11434/v1"

    def test_env_override_model(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")
        adapter = OllamaAdapter()
        assert adapter.config.model == "mistral"

    def test_explicit_config_override(self):
        config = AdapterConfig(
            api_key="sk-test",
            base_url="http://explicit:11434/v1",
            model="codellama",
        )
        adapter = OllamaAdapter(config)
        assert adapter.config.base_url == "http://explicit:11434/v1"
        assert adapter.config.model == "codellama"


class TestOllamaRun:
    pytestmark = pytest.mark.asyncio

    @patch("openai.AsyncOpenAI")
    async def test_returns_text(self, mock_openai):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("Hello from Ollama")])
        )
        mock_openai.return_value = mock_client
        adapter = OllamaAdapter()
        adapter.client = mock_client

        response = await adapter.run(prompt="Say hi")
        assert response.text == "Hello from Ollama"
        assert response.latency_seconds >= 0

    @patch("openai.AsyncOpenAI")
    async def test_uses_ollama_defaults(self, mock_openai):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_response(choices=[_mock_choice("OK")])
        )
        mock_openai.return_value = mock_client
        adapter = OllamaAdapter()
        adapter.client = mock_client

        await adapter.run(prompt="Hi")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == OLLAMA_DEFAULT_MODEL
