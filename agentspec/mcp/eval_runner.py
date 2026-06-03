from __future__ import annotations

import asyncio
import os

from agentspec.adapters.openai_compatible_adapter import (
    AdapterConfig,
    OpenAICompatibleAdapter,
)
from agentspec.mcp.protocol import BaseMcpServer
from agentspec.runner import TestRunner
from agentspec.spec import Spec


def _report_to_dict(report) -> dict:
    return {
        "spec_name": report.spec_name,
        "summary": {
            "total": report.summary.total,
            "passed": report.summary.passed,
            "failed": report.summary.failed,
            "errors": report.summary.errors,
            "pass_rate": report.summary.pass_rate,
        },
        "avg_latency": report.avg_latency,
        "total_tokens": report.total_tokens,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "error": r.error,
                "latency_seconds": r.latency_seconds,
                "token_usage": r.token_usage,
                "assertion_results": [
                    {"name": a.name, "passed": a.passed, "reason": a.reason}
                    for a in r.assertion_results
                ],
            }
            for r in report.results
        ],
    }


def _build_adapter(
    model: str | None,
    base_url: str | None,
    api_key: str | None,
) -> OpenAICompatibleAdapter:
    config = AdapterConfig(
        api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        model=model or "deepseek-v4-pro",
    )
    return OpenAICompatibleAdapter(config)


def run_eval(
    spec_path: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    try:
        spec = Spec.from_yaml(spec_path)
    except Exception as exc:
        return {"error": f"Failed to parse spec: {exc}"}
    adapter = _build_adapter(model, base_url, api_key)
    runner = TestRunner(spec, adapter)
    report = asyncio.run(runner.run_all())
    return _report_to_dict(report)


def run_single_test(
    spec_path: str,
    test_name: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    try:
        spec = Spec.from_yaml(spec_path)
    except Exception as exc:
        return {"error": f"Failed to parse spec: {exc}"}

    matching = [t for t in spec.tests if t.name == test_name]
    if not matching:
        return {"error": f"Test '{test_name}' not found in spec"}
    spec.tests = matching  # only run the matching test
    adapter = _build_adapter(model, base_url, api_key)
    runner = TestRunner(spec, adapter)
    report = asyncio.run(runner.run_all())
    return _report_to_dict(report)


_server: BaseMcpServer | None = None


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("eval-runner")

    srv.tool(
        "run_eval",
        description="Run a full agent evaluation against a spec file",
        input_schema={
            "type": "object",
            "properties": {
                "spec_path": {
                    "type": "string",
                    "description": "Path to the spec YAML file",
                },
                "model": {"type": "string", "description": "Override model name"},
                "base_url": {"type": "string", "description": "Override API base URL"},
                "api_key": {"type": "string", "description": "Override API key"},
            },
            "required": ["spec_path"],
        },
    )(run_eval)

    srv.tool(
        "run_single_test",
        description="Run a single test case from a spec file by name",
        input_schema={
            "type": "object",
            "properties": {
                "spec_path": {
                    "type": "string",
                    "description": "Path to the spec YAML file",
                },
                "test_name": {
                    "type": "string",
                    "description": "Name of the test case to run",
                },
                "model": {"type": "string", "description": "Override model name"},
                "base_url": {"type": "string", "description": "Override API base URL"},
                "api_key": {"type": "string", "description": "Override API key"},
            },
            "required": ["spec_path", "test_name"],
        },
    )(run_single_test)

    _server = srv
    return srv


def main() -> None:
    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
