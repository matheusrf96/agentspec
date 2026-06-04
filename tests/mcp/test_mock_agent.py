from __future__ import annotations

import tempfile

import pytest
import yaml

from agentspec.mcp.mock_agent import (
    BEHAVIOR_TEMPLATES,
    create_mock,
    destroy_mock,
    list_behaviors,
    run_with_mock,
    set_behavior,
)

ALWAYS_PASS_SPEC = {
    "name": "Mock Test",
    "model": "mock",
    "system_prompt": "You are a test assistant.",
    "tests": [
        {
            "name": "test1",
            "prompt": "Hello",
            "assertions": [{"type": "output_contains", "value": "Hello"}],
        },
    ],
}


def _write_spec(data: dict) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return f.name


class TestCreateMock:
    def test_creates_mock_with_generated_id(self):
        result = create_mock()
        assert "agent_id" in result
        assert result["agent_id"].startswith("mock-")

    def test_creates_mock_with_custom_name(self):
        result = create_mock(name="my-custom-mock")
        assert result["agent_id"] == "my-custom-mock"


class TestDestroyMock:
    def test_destroys_existing_mock(self):
        result = create_mock(name="to-destroy")
        agent_id = result["agent_id"]
        destroy_result = destroy_mock(agent_id)
        assert destroy_result["ok"] is True

    def test_destroy_nonexistent_mock_returns_error(self):
        result = destroy_mock("nonexistent")
        assert result["ok"] is False
        assert "error" in result


class TestSetBehavior:
    def test_sets_behaviors_successfully(self):
        create_result = create_mock(name="behavior-test")
        agent_id = create_result["agent_id"]
        result = set_behavior(
            agent_id,
            [
                {
                    "step": 0,
                    "response": {"text": "Hello there!", "latency_seconds": 0.0},
                },
            ],
        )
        assert result["ok"] is True
        assert result["behavior_count"] == 1

    def test_set_behavior_nonexistent_mock(self):
        result = set_behavior("nonexistent", [{"step": 0, "response": {"text": "hi"}}])
        assert result["ok"] is False

    def test_set_multiple_behaviors(self):
        create_result = create_mock(name="multi-behavior")
        agent_id = create_result["agent_id"]
        result = set_behavior(
            agent_id,
            [
                {"step": 0, "response": {"text": "First"}},
                {"step": 1, "response": {"text": "Second"}},
                {"step": 2, "response": {"text": "Third"}},
            ],
        )
        assert result["ok"] is True
        assert result["behavior_count"] == 3


class TestRunWithMock:
    def test_basic_text_response(self):
        create_result = create_mock(name="basic-mock")
        agent_id = create_result["agent_id"]
        set_behavior(
            agent_id,
            [
                {
                    "step": 0,
                    "response": {"text": "Hello there!", "latency_seconds": 0.0},
                },
            ],
        )
        spec_path = _write_spec(ALWAYS_PASS_SPEC)
        try:
            result = run_with_mock(spec_path, agent_id)
            assert "error" not in result
            assert result["spec_name"] == "Mock Test"
            assert result["summary"]["total"] == 1
            assert result["results"][0]["passed"] is True
        finally:
            import os

            os.unlink(spec_path)

    def test_multiple_tests(self):
        create_result = create_mock(name="multi-test-mock")
        agent_id = create_result["agent_id"]
        set_behavior(
            agent_id,
            [
                {"step": 0, "response": {"text": "First", "latency_seconds": 0.0}},
                {"step": 1, "response": {"text": "Second", "latency_seconds": 0.0}},
            ],
        )
        spec_data = {
            "name": "Multi Test",
            "model": "mock",
            "tests": [
                {
                    "name": "t1",
                    "prompt": "hi",
                    "assertions": [{"type": "output_contains", "value": "First"}],
                },
                {
                    "name": "t2",
                    "prompt": "bye",
                    "assertions": [{"type": "output_contains", "value": "Second"}],
                },
            ],
        }
        spec_path = _write_spec(spec_data)
        try:
            result = run_with_mock(spec_path, agent_id)
            assert result["summary"]["total"] == 2
            assert result["summary"]["passed"] == 2
        finally:
            import os

            os.unlink(spec_path)

    def test_tool_call_behavior(self):
        create_result = create_mock(name="tool-mock")
        agent_id = create_result["agent_id"]
        set_behavior(
            agent_id,
            [
                {
                    "step": 0,
                    "response": {
                        "text": "The price is $150",
                        "tool_calls": [
                            {"name": "get_stock_price", "args": {"symbol": "AAPL"}}
                        ],
                        "latency_seconds": 0.0,
                    },
                },
            ],
        )
        spec_data = {
            "name": "Tool Test",
            "model": "mock",
            "tests": [
                {
                    "name": "tool_test",
                    "prompt": "What is AAPL at?",
                    "assertions": [
                        {"type": "tool_called", "tool_name": "get_stock_price"},
                        {"type": "output_matches", "pattern": r"\$\d+"},
                    ],
                },
            ],
        }
        spec_path = _write_spec(spec_data)
        try:
            result = run_with_mock(spec_path, agent_id)
            assert result["summary"]["passed"] == 1
            assert result["summary"]["total"] == 1
        finally:
            import os

            os.unlink(spec_path)

    def test_nonexistent_mock_returns_error(self):
        result = run_with_mock("spec.yaml", "nonexistent")
        assert "error" in result

    def test_nonexistent_spec_returns_error(self):
        create_result = create_mock(name="spec-error-mock")
        agent_id = create_result["agent_id"]
        result = run_with_mock("/nonexistent/spec.yaml", agent_id)
        assert "error" in result


class TestListBehaviors:
    def test_lists_all_templates(self):
        result = list_behaviors()
        assert "templates" in result
        assert len(result["templates"]) == len(BEHAVIOR_TEMPLATES)
        names = [t["name"] for t in result["templates"]]
        assert "always_pass" in names
        assert "always_fail" in names
        assert "tool_caller" in names

    def test_templates_have_descriptions(self):
        result = list_behaviors()
        for t in result["templates"]:
            assert "description" in t
            assert len(t["description"]) > 0


class TestBehaviorMatching:
    @pytest.mark.asyncio
    async def test_behavior_with_tool_name_filter(self):
        from agentspec.mcp.mock_agent import MockAdapter

        adapter = MockAdapter()
        adapter.configure(
            [
                {
                    "step": 0,
                    "on": {"tool_name": "get_weather"},
                    "response": {
                        "tool_calls": [{"name": "search", "args": {"q": "test"}}],
                        "text": "ok",
                    },
                },
            ]
        )
        resp = await adapter.run(prompt="hello")
        assert resp.text == ""
        assert resp.tool_calls == []

    @pytest.mark.asyncio
    async def test_behavior_with_prompt_matches(self):
        from agentspec.mcp.mock_agent import MockAdapter

        adapter = MockAdapter()
        adapter.configure(
            [
                {
                    "step": 0,
                    "on": {"prompt_matches": "weather"},
                    "response": {"text": "weather result"},
                },
            ]
        )
        resp = await adapter.run(prompt="tell me the weather")
        assert resp.text == "weather result"

    @pytest.mark.asyncio
    async def test_behavior_prompt_matches_skips(self):
        """Line 57: prompt_match doesn't match, skip"""
        from agentspec.mcp.mock_agent import MockAdapter

        adapter = MockAdapter()
        adapter.configure(
            [
                {
                    "step": 0,
                    "on": {"prompt_matches": "weather"},
                    "response": {"text": "weather result"},
                },
            ]
        )
        resp = await adapter.run(prompt="tell me about sports")
        assert resp.text == ""

    @pytest.mark.asyncio
    async def test_behavior_with_latency(self):
        from agentspec.mcp.mock_agent import MockAdapter

        adapter = MockAdapter()
        adapter.configure(
            [
                {
                    "step": 0,
                    "on": {},
                    "response": {"text": "slow", "latency_seconds": 0.01},
                },
            ]
        )
        resp = await adapter.run(prompt="hi")
        assert resp.text == "slow"
        assert resp.latency_seconds > 0

    @pytest.mark.asyncio
    async def test_behavior_no_match_falls_through(self):
        from agentspec.mcp.mock_agent import MockAdapter

        adapter = MockAdapter()
        adapter.configure(
            [
                {
                    "step": 5,
                    "on": {},
                    "response": {"text": "never"},
                },
            ]
        )
        resp = await adapter.run(prompt="hi")
        assert resp.text == ""
        assert resp.latency_seconds == 0.0


class TestBuildServer:
    def test_build_server_returns_server(self):
        from agentspec.mcp.mock_agent import _build_server

        srv = _build_server()
        assert srv is not None
        assert srv.server_name == "mock-agent"


class TestMockAgentTools:
    def test_list_behaviors(self):
        from agentspec.mcp.mock_agent import list_behaviors

        result = list_behaviors()
        assert isinstance(result, dict)
        assert "templates" in result
        assert len(result["templates"]) > 0

    def test_destroy_mock_not_found(self):
        from agentspec.mcp.mock_agent import destroy_mock

        result = destroy_mock("nonexistent")
        assert "error" in result

    def test_create_and_destroy_mock(self):
        from agentspec.mcp.mock_agent import create_mock, destroy_mock

        created = create_mock("test-agent")
        aid = created.get("agent_id")
        assert aid is not None
        destroyed = destroy_mock(aid)
        assert "destroyed" in str(destroyed).lower() or "ok" in str(destroyed).lower()
