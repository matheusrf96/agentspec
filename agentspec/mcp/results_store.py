from __future__ import annotations

from agentspec.mcp.protocol import BaseMcpServer
from agentspec.results_backend import JsonFileBackend, ResultsBackend

_backend: ResultsBackend | None = None


def _get_backend() -> ResultsBackend:
    global _backend
    if _backend is None:
        _backend = JsonFileBackend()
    return _backend


def save_result(report: dict, spec_path: str | None = None) -> dict:
    return _get_backend().save_result(report, spec_path)


def list_runs(limit: int | None = None, spec_name: str | None = None) -> dict:
    return _get_backend().list_runs(limit=limit, spec_name=spec_name)


def get_run(run_id: str) -> dict:
    return _get_backend().get_run(run_id)


def compare_runs(id1: str, id2: str) -> dict:
    return _get_backend().compare_runs(id1, id2)


def get_trends(spec_name: str | None = None, days: int | None = None) -> dict:
    return _get_backend().get_trends(spec_name=spec_name, days=days)


def prune_runs(keep: int = 50, spec_name: str | None = None) -> dict:
    return _get_backend().prune_runs(keep=keep, spec_name=spec_name)


_server: BaseMcpServer | None = None


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("results-store")

    srv.tool(
        "save_result",
        description="Save an evaluation result to persistent storage."
        " Returns a run_id.",
        input_schema={
            "type": "object",
            "properties": {
                "report": {
                    "type": "object",
                    "description": "Evaluation report dict",
                },
                "spec_path": {
                    "type": "string",
                    "description": "Optional spec file path",
                },
            },
            "required": ["report"],
        },
    )(save_result)

    srv.tool(
        "list_runs",
        description="List past evaluation runs, with optional limit"
        " and spec name filter",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of runs to return",
                },
                "spec_name": {
                    "type": "string",
                    "description": "Filter by spec name",
                },
            },
        },
    )(list_runs)

    srv.tool(
        "get_run",
        description="Get full details of a specific evaluation run by run_id",
        input_schema={
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Run ID from save_result",
                },
            },
            "required": ["run_id"],
        },
    )(get_run)

    srv.tool(
        "compare_runs",
        description="Compare two evaluation runs and return the differences",
        input_schema={
            "type": "object",
            "properties": {
                "id1": {"type": "string", "description": "First run ID"},
                "id2": {
                    "type": "string",
                    "description": "Second run ID",
                },
            },
            "required": ["id1", "id2"],
        },
    )(compare_runs)

    srv.tool(
        "prune_runs",
        description="Remove old evaluation runs, keeping the most recent N.",
        input_schema={
            "type": "object",
            "properties": {
                "keep": {
                    "type": "integer",
                    "description": "Number of recent runs to keep",
                },
                "spec_name": {
                    "type": "string",
                    "description": "Filter by spec name",
                },
            },
        },
    )(prune_runs)

    srv.tool(
        "get_trends",
        description="Get pass rate trends over time, optionally"
        " filtered by spec and time window",
        input_schema={
            "type": "object",
            "properties": {
                "spec_name": {
                    "type": "string",
                    "description": "Filter by spec name",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to include",
                },
            },
        },
    )(get_trends)

    _server = srv
    return srv


def main() -> None:  # pragma: no cover
    import asyncio

    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()  # pragma: no cover
