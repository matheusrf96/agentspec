from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentspec.adapters.openai_compatible_adapter import (
    OpenAICompatibleAdapter,
)
from agentspec.runner import TestRunner
from agentspec.spec import (
    CannedResponse,
    ConversationEntry,
    Fixtures,
    MockTool,
    Spec,
    TestCase,
    ToolCalledAssertion,
)


class TestSpecFixtureParsing:
    def test_spec_with_fixtures(self):
        data = {
            "name": "Fixture Spec",
            "model": "gpt-4",
            "fixtures": {
                "conversation_history": [
                    {"role": "user", "content": "Previous question"},
                    {
                        "role": "assistant",
                        "content": "Previous answer",
                        "tool_calls": [{"name": "search", "args": {"q": "test"}}],
                    },
                ],
                "mock_tools": [
                    {
                        "name": "get_weather",
                        "description": "Get weather",
                        "response": '{"temp": 22}',
                    }
                ],
                "canned_responses": [
                    {
                        "prompt_contains": "hello",
                        "output": "Hi there!",
                        "tool_calls": [{"name": "greet", "args": {"name": "world"}}],
                    }
                ],
            },
            "tests": [
                {
                    "name": "t1",
                    "prompt": "say hello",
                    "assertions": [{"type": "output_contains", "value": "hello"}],
                }
            ],
        }
        spec = Spec.model_validate(data)
        assert spec.fixtures is not None
        assert len(spec.fixtures.conversation_history) == 2
        assert len(spec.fixtures.mock_tools) == 1
        assert len(spec.fixtures.canned_responses) == 1
        assert spec.fixtures.mock_tools[0].name == "get_weather"
        assert spec.fixtures.canned_responses[0].prompt_contains == "hello"

    def test_spec_without_fixtures(self):
        spec = Spec(name="Plain", tests=[])
        assert spec.fixtures is None

    def test_from_yaml_string_with_fixtures(self):
        yaml_str = """
name: YAML Spec
model: gpt-4
fixtures:
  conversation_history:
    - role: user
      content: "Preload"
  canned_responses:
    - prompt_contains: test
      output: "response"
tests:
  - name: t1
    prompt: test
    assertions:
      - type: output_contains
        value: response
"""
        spec = Spec.from_yaml_string(yaml_str)
        assert spec.fixtures is not None
        assert len(spec.fixtures.conversation_history) == 1
        assert spec.fixtures.conversation_history[0].content == "Preload"


class TestFixtureModels:
    def test_conversation_entry(self):
        entry = ConversationEntry(
            role="assistant",
            content="Hello",
            tool_calls=[{"name": "search", "args": {"q": "test"}}],
        )
        assert entry.role == "assistant"
        tcs = entry.tool_calls
        assert tcs is not None
        assert tcs[0]["name"] == "search"

    def test_mock_tool_defaults(self):
        tool = MockTool(name="search", response="result")
        assert tool.description is None

    def test_canned_response_defaults(self):
        cr = CannedResponse(prompt_contains="hi")
        assert cr.output == ""
        assert cr.tool_calls is None

    def test_fixtures_defaults(self):
        f = Fixtures()
        assert f.conversation_history == []
        assert f.mock_tools == []
        assert f.canned_responses == []


@pytest.mark.asyncio
class TestCannedResponses:
    async def test_canned_response_matches_prompt(self):
        spec = Spec(
            name="Canned",
            fixtures=Fixtures(
                canned_responses=[
                    CannedResponse(
                        prompt_contains="hello",
                        output="Hi back!",
                    )
                ]
            ),
            tests=[TestCase(name="t1", prompt="say hello please", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        # Patch the client to ensure we don't actually call the API
        adapter.client = AsyncMock()
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()
        assert report.results[0].passed is True
        assert report.results[0].latency_seconds == 0.0

    async def test_canned_response_with_tool_calls(self):
        spec = Spec(
            name="Canned Tools",
            fixtures=Fixtures(
                canned_responses=[
                    CannedResponse(
                        prompt_contains="price",
                        output="The price is $100",
                        tool_calls=[{"name": "get_price", "args": {"symbol": "AAPL"}}],
                    )
                ]
            ),
            tests=[
                TestCase(
                    name="t1",
                    prompt="what is the price",
                    assertions=[
                        ToolCalledAssertion(tool_name="get_price"),
                    ],
                )
            ],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        adapter.client = AsyncMock()
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()
        assert report.results[0].passed is True

    async def test_canned_no_match_falls_through(self):
        spec = Spec(
            name="No Match",
            fixtures=Fixtures(
                canned_responses=[
                    CannedResponse(
                        prompt_contains="not-in-prompt",
                        output="Should not match",
                    )
                ]
            ),
            tests=[TestCase(name="t1", prompt="something else", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "real response"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()
        assert report.results[0].passed is True


@pytest.mark.asyncio
class TestConversationHistory:
    async def test_conversation_history_prepended(self):
        spec = Spec(
            name="History",
            fixtures=Fixtures(
                conversation_history=[
                    ConversationEntry(role="assistant", content="Previous answer"),
                ]
            ),
            tests=[TestCase(name="t1", prompt="new question", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "response"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        await runner.run_all()
        call_args = mock_client.chat.completions.create.call_args
        msgs = call_args[1]["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "assistant"
        assert msgs[0]["content"] == "Previous answer"
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "new question"

    async def test_conversation_history_with_system_prompt(self):
        spec = Spec(
            name="History+System",
            system_prompt="Be helpful",
            fixtures=Fixtures(
                conversation_history=[
                    ConversationEntry(role="user", content="old question"),
                ]
            ),
            tests=[TestCase(name="t1", prompt="new q", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        await runner.run_all()
        call_args = mock_client.chat.completions.create.call_args
        msgs = call_args[1]["messages"]
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "old question"
        assert msgs[2]["role"] == "user"
        assert msgs[2]["content"] == "new q"


@pytest.mark.asyncio
class TestMockTools:
    async def test_mock_tools_passed_to_adapter(self):
        spec = Spec(
            name="Mock Tools",
            fixtures=Fixtures(
                mock_tools=[
                    MockTool(
                        name="get_stock",
                        description="Get stock price",
                        response='{"price": 100}',
                    ),
                ]
            ),
            tests=[TestCase(name="t1", prompt="get stock", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        await runner.run_all()
        create_kwargs = mock_client.chat.completions.create.call_args[1]
        tools = create_kwargs.get("tools")
        assert tools is not None
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "get_stock"


class TestConversationHistoryEdgeCases:
    @pytest.mark.asyncio
    async def test_history_with_tool_calls(self):
        spec = Spec(
            name="Hist Tools",
            fixtures=Fixtures(
                conversation_history=[
                    ConversationEntry(
                        role="assistant",
                        content="Let me search",
                        tool_calls=[{"name": "search", "args": {"q": "test"}}],
                    ),
                ]
            ),
            tests=[TestCase(name="t1", prompt="next", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        await runner.run_all()
        call_args = mock_client.chat.completions.create.call_args
        msgs = call_args[1]["messages"]
        assert len(msgs) == 2
        assert "tool_calls" in msgs[0]
        assert msgs[0]["tool_calls"][0]["name"] == "search"


class TestRunnerErrorPath:
    @pytest.mark.asyncio
    async def test_adapter_error_is_caught(self):
        spec = Spec(
            name="Error Spec",
            tests=[TestCase(name="t1", prompt="hello", assertions=[])],
        )
        adapter = OpenAICompatibleAdapter(
            MagicMock(api_key="test", base_url="http://test")
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=ValueError("API failure")
        )
        adapter.client = mock_client
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()
        assert report.results[0].passed is False
        err = report.results[0].error
        assert err is not None
        assert "ValueError" in err
