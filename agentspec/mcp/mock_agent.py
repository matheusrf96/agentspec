from __future__ import annotations

import asyncio
import json
import uuid

from agentspec.adapters.base import AgentAdapter, AgentResponse, ToolCall
from agentspec.mcp.protocol import BaseMcpServer
from agentspec.runner import TestRunner
from agentspec.spec import Spec

BEHAVIOR_TEMPLATES: dict[str, str] = {
    "always_pass": "Responds with success for every test case. All assertions pass.",
    "always_fail": "Responds with empty/failure output. Most assertions fail.",
    "tool_caller": "Calls the specified tool with sample arguments on each prompt.",
    "slow_responder": "Responds correctly but with configurable latency (default 5s).",
    "json_responder": "Returns valid JSON output matching a schema.",
    "multi_step": "Sequences multiple behaviors across successive test calls.",
}


class MockAdapter(AgentAdapter):
    def __init__(self) -> None:
        self._behaviors: list[dict] = []
        self._step_counter: int = 0

    def configure(self, behaviors: list[dict]) -> None:
        self._behaviors = list(behaviors)
        self._step_counter = 0

    async def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        fixtures: dict | None = None,
    ) -> AgentResponse:
        for behavior in self._behaviors:
            step = behavior.get("step", 0)
            on = behavior.get("on") or {}
            resp_data = behavior.get("response", {})

            if step != self._step_counter:
                continue

            if on:
                tool_name_filter = on.get("tool_name")
                prompt_match = on.get("prompt_matches")
                if tool_name_filter:
                    calls_str = str(resp_data.get("tool_calls", []))
                    if tool_name_filter not in calls_str:
                        continue
                if prompt_match:
                    import re

                    if not re.search(prompt_match, prompt):
                        continue

            self._step_counter += 1

            tool_calls_raw = resp_data.get("tool_calls", [])
            tool_calls = [
                ToolCall(
                    name=tc.get("name", ""),
                    args=(
                        json.loads(tc.get("args", "{}"))
                        if isinstance(tc.get("args"), str)
                        else tc.get("args", {})
                    ),
                )
                for tc in tool_calls_raw
            ]
            latency = resp_data.get("latency_seconds", 0.0)
            if latency > 0:
                await asyncio.sleep(latency)
            return AgentResponse(
                text=resp_data.get("text", ""),
                tool_calls=tool_calls,
                latency_seconds=latency,
                token_usage={
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            )

        return AgentResponse(text="", latency_seconds=0.0)

    def get_templates_json(self) -> list[dict]:
        return [
            {"name": name, "description": desc}
            for name, desc in BEHAVIOR_TEMPLATES.items()
        ]


_mock_agents: dict[str, MockAdapter] = {}


def create_mock(name: str | None = None) -> dict:
    agent_id = name or f"mock-{uuid.uuid4().hex[:8]}"
    _mock_agents[agent_id] = MockAdapter()
    return {"agent_id": agent_id}


def set_behavior(agent_id: str, behaviors: list[dict]) -> dict:
    adapter = _mock_agents.get(agent_id)
    if adapter is None:
        return {"ok": False, "error": f"Mock agent not found: {agent_id}"}
    adapter.configure(behaviors)
    return {"ok": True, "behavior_count": len(behaviors)}


def run_with_mock(spec_path: str, agent_id: str) -> dict:
    adapter = _mock_agents.get(agent_id)
    if adapter is None:
        return {"error": f"Mock agent not found: {agent_id}"}
    try:
        spec = Spec.from_yaml(spec_path)
    except Exception as exc:
        return {"error": f"Failed to parse spec: {exc}"}
    runner = TestRunner(spec, adapter)
    report = asyncio.run(runner.run_all())
    return json.loads(
        json.dumps(
            {
                "spec_name": report.spec_name,
                "summary": {
                    "total": report.summary.total,
                    "passed": report.summary.passed,
                    "failed": report.summary.failed,
                    "errors": report.summary.errors,
                    "pass_rate": report.summary.pass_rate,
                },
                "results": [
                    {
                        "name": r.name,
                        "passed": r.passed,
                        "error": r.error,
                        "latency_seconds": r.latency_seconds,
                        "assertion_results": [
                            {"name": a.name, "passed": a.passed, "reason": a.reason}
                            for a in r.assertion_results
                        ],
                    }
                    for r in report.results
                ],
            },
            default=str,
        )
    )


def list_behaviors() -> dict:
    return {
        "templates": [
            {"name": name, "description": desc}
            for name, desc in BEHAVIOR_TEMPLATES.items()
        ],
    }


def destroy_mock(agent_id: str) -> dict:
    if agent_id in _mock_agents:
        del _mock_agents[agent_id]
        return {"ok": True}
    return {"ok": False, "error": f"Mock agent not found: {agent_id}"}


_server: BaseMcpServer | None = None

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "create_mock": "Create a new mock agent with a unique ID",
    "set_behavior": "Configure a mock agent's response behaviors"
    " (supports sequential scripting)",
    "run_with_mock": "Run a spec file against a mock agent and return results",
    "list_behaviors": "List available behavior templates",
    "destroy_mock": "Remove a mock agent and free its resources",
}

_INPUT_SCHEMAS: dict[str, dict] = {
    "create_mock": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Optional name for the mock agent"
                " (auto-generated if omitted)",
            },
        },
    },
    "set_behavior": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "Mock agent ID from create_mock",
            },
            "behaviors": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of behavior configs with"
                " step, on, and response fields",
            },
        },
        "required": ["agent_id", "behaviors"],
    },
    "run_with_mock": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "description": "Path to the spec file"},
            "agent_id": {
                "type": "string",
                "description": "Mock agent ID from create_mock",
            },
        },
        "required": ["spec_path", "agent_id"],
    },
    "list_behaviors": {
        "type": "object",
        "properties": {},
    },
    "destroy_mock": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "Mock agent ID to destroy"},
        },
        "required": ["agent_id"],
    },
}


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("mock-agent")
    for name in (
        "create_mock",
        "set_behavior",
        "run_with_mock",
        "list_behaviors",
        "destroy_mock",
    ):
        desc = _TOOL_DESCRIPTIONS.get(name, "")
        schema = _INPUT_SCHEMAS.get(name, {"type": "object", "properties": {}})
        func = globals()[name]
        srv.tool(name, description=desc, input_schema=schema)(func)
    _server = srv
    return srv


def main() -> None:  # pragma: no cover
    import asyncio

    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()  # pragma: no cover
