from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agentspec.adapters.langchain_adapter import (
    LangChainAdapter,
    LangChainAdapterConfig,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_runnable():
    runnable = AsyncMock()
    return runnable


class _FakeUsage:
    input_tokens = 10
    output_tokens = 20
    total_tokens = 30


class _FakeMsg:
    def __init__(self, content: str = "Hello!", tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage_metadata: _FakeUsage | None = _FakeUsage()


def _make_msg(content: str = "Hello!", tool_calls: list | None = None) -> _FakeMsg:
    return _FakeMsg(content=content, tool_calls=tool_calls)


class TestTextResponse:
    async def test_returns_text(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="Hello from LangChain")
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Say hello")
        assert response.text == "Hello from LangChain"
        assert response.tool_calls == []

    async def test_empty_content(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="")
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Say nothing")
        assert response.text == ""

    async def test_no_tool_calls_by_default(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="Hi")
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.tool_calls == []


class TestToolCalls:
    async def test_extracts_tool_calls(self, mock_runnable):
        msg = _make_msg(
            content="",
            tool_calls=[
                {
                    "name": "get_weather",
                    "args": {"city": "London"},
                    "id": "1",
                    "type": "tool_call",
                }
            ],
        )
        mock_runnable.ainvoke.return_value = msg
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Get weather")
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"
        assert response.tool_calls[0].args == {"city": "London"}

    async def test_multiple_tool_calls(self, mock_runnable):
        msg = _make_msg(
            content="",
            tool_calls=[
                {
                    "name": "search",
                    "args": {"q": "weather"},
                    "id": "1",
                    "type": "tool_call",
                },
                {
                    "name": "calculate",
                    "args": {"expr": "1+1"},
                    "id": "2",
                    "type": "tool_call",
                },
            ],
        )
        mock_runnable.ainvoke.return_value = msg
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Do things")
        assert len(response.tool_calls) == 2


class TestSystemPrompt:
    async def test_passes_system_prompt(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="OK")
        adapter = LangChainAdapter(mock_runnable)
        await adapter.run(prompt="Hi", system_prompt="Be helpful")
        call_args = mock_runnable.ainvoke.call_args
        msgs = call_args[0][0]
        assert len(msgs) == 2
        assert msgs[0].content == "Be helpful"
        assert msgs[1].content == "Hi"

    async def test_no_system_prompt_when_none(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="OK")
        adapter = LangChainAdapter(mock_runnable)
        await adapter.run(prompt="Hi")
        call_args = mock_runnable.ainvoke.call_args
        msgs = call_args[0][0]
        assert len(msgs) == 1
        assert msgs[0].content == "Hi"


class TestTokenUsage:
    async def test_extracts_token_usage(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="Hi")
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.token_usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    async def test_no_usage_when_none(self, mock_runnable):
        msg = _make_msg(content="Hi")
        msg.usage_metadata = None
        mock_runnable.ainvoke.return_value = msg
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.token_usage is None


class TestDictResponse:
    async def test_handles_dict_output(self, mock_runnable):
        mock_runnable.ainvoke.return_value = {"content": "Hello", "tool_calls": []}
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.text == "Hello"

    async def test_dict_with_tool_calls(self, mock_runnable):
        mock_runnable.ainvoke.return_value = {
            "content": "",
            "tool_calls": [{"name": "search", "args": {"q": "test"}}],
        }
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Search")
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "search"

    async def test_dict_fallback_to_output_key(self, mock_runnable):
        mock_runnable.ainvoke.return_value = {"output": "result"}
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Go")
        assert response.text == "result"


class TestFallbackToDict:
    async def test_falls_back_to_dict_input_on_error(self, mock_runnable):
        async def side_effect(*args, **kwargs):
            msgs = args[0]
            if isinstance(msgs, list):
                raise ValueError("expected dict")
            return {"output": "from dict"}

        mock_runnable.ainvoke.side_effect = side_effect
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi", system_prompt="Help")
        assert response.text == "from dict"


class TestModelOverride:
    async def test_uses_model_override(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="OK")
        adapter = LangChainAdapter(mock_runnable)
        await adapter.run(prompt="Hi", model="gpt-4")

    async def test_uses_configured_model(self, mock_runnable):
        mock_runnable.ainvoke.return_value = _make_msg(content="OK")
        config = LangChainAdapterConfig(model="claude-3")
        adapter = LangChainAdapter(mock_runnable, config=config)
        await adapter.run(prompt="Hi")


class TestLatency:
    async def test_records_latency(self, mock_runnable):
        import asyncio

        async def slow(*args, **kwargs):
            await asyncio.sleep(0.05)
            return _make_msg(content="Hi")

        mock_runnable.ainvoke.side_effect = slow
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.latency_seconds >= 0.05


class TestConfig:
    async def test_default_config(self):
        adapter = LangChainAdapter(AsyncMock())
        assert adapter.config.temperature == 0.0
        assert adapter.config.model is None
        assert adapter.config.max_tokens is None

    async def test_custom_config(self):
        config = LangChainAdapterConfig(
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
        )
        adapter = LangChainAdapter(AsyncMock(), config=config)
        assert adapter.config.model == "gpt-4"
        assert adapter.config.temperature == 0.7
        assert adapter.config.max_tokens == 2000


class TestImportError:
    async def test_human_system_message_fallbacks_to_none(self):
        import builtins
        import importlib
        from unittest import mock

        import agentspec.adapters.langchain_adapter as mod

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "langchain_core" or name.startswith("langchain_core."):
                raise ImportError(f"No module named {name}")
            return original_import(name, *args, **kwargs)

        with mock.patch.object(builtins, "__import__", _mock_import):
            importlib.reload(mod)
            assert mod.HumanMessage is None
            assert mod.SystemMessage is None

        importlib.reload(mod)


class TestFallbackResult:
    async def test_unknown_result_type_fallback_to_str(self, mock_runnable):
        mock_runnable.ainvoke.return_value = 42
        adapter = LangChainAdapter(mock_runnable)
        response = await adapter.run(prompt="Hi")
        assert response.text == "42"
        assert response.tool_calls == []
