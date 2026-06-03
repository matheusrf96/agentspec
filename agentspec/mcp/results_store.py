from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agentspec.mcp.protocol import BaseMcpServer

RESULTS_DIR = Path.home() / ".agentspec" / "results"
INDEX_FILE = RESULTS_DIR / "index.json"


def _ensure_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> dict:
    _ensure_dir()
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"runs": []}


def _save_index(index: dict) -> None:
    _ensure_dir()
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_result(report: dict, spec_path: str | None = None) -> dict:
    run_id = uuid.uuid4().hex[:12]
    timestamp = _iso_now()
    summary = report.get("summary", {})
    entry = {
        "run_id": run_id,
        "spec_name": report.get("spec_name", "unknown"),
        "spec_path": spec_path,
        "timestamp": timestamp,
        "pass_rate": summary.get("pass_rate", 0.0),
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": summary.get("errors", 0),
    }
    index = _load_index()
    index["runs"].insert(0, entry)
    _save_index(index)

    run_file = RESULTS_DIR / f"{run_id}.json"
    with open(run_file, "w") as f:
        payload = {"run_id": run_id, "timestamp": timestamp, "report": report}
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    return {"run_id": run_id}


def list_runs(limit: int | None = None, spec_name: str | None = None) -> dict:
    index = _load_index()
    runs = index.get("runs", [])
    if spec_name:
        runs = [r for r in runs if r.get("spec_name") == spec_name]
    if limit is not None and limit > 0:
        runs = runs[:limit]
    return {"runs": runs}


def get_run(run_id: str) -> dict:
    run_file = RESULTS_DIR / f"{run_id}.json"
    if not run_file.exists():
        return {"error": f"Run not found: {run_id}"}
    try:
        with open(run_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return {"error": f"Failed to read run: {exc}"}


def compare_runs(id1: str, id2: str) -> dict:
    run1 = get_run(id1)
    run2 = get_run(id2)
    if "error" in run1:
        return {"error": run1["error"]}
    if "error" in run2:
        return {"error": run2["error"]}

    report1 = run1.get("report", {})
    report2 = run2.get("report", {})

    results1 = {r["name"]: r for r in report1.get("results", [])}
    results2 = {r["name"]: r for r in report2.get("results", [])}

    all_names = set(results1) | set(results2)
    differences = []

    def _status(r: dict | None) -> str:
        if r is None:
            return "missing"
        if r.get("error"):
            return "error"
        return "pass" if r.get("passed") else "fail"

    for name in sorted(all_names):
        r1 = results1.get(name)
        r2 = results2.get(name)
        status_before = _status(r1)
        status_after = _status(r2)
        if status_before != status_after:
            differences.append({
                "test_name": name,
                "status_before": status_before,
                "status_after": status_after,
            })

    return {
        "run1": {"run_id": id1, "timestamp": run1.get("timestamp")},
        "run2": {"run_id": id2, "timestamp": run2.get("timestamp")},
        "differences": differences,
        "summary1": report1.get("summary"),
        "summary2": report2.get("summary"),
    }


def get_trends(spec_name: str | None = None, days: int | None = None) -> dict:
    from datetime import timedelta
    index = _load_index()
    runs = index.get("runs", [])

    if spec_name:
        runs = [r for r in runs if r.get("spec_name") == spec_name]

    if days is not None and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        runs = [r for r in runs if _parse_iso(r.get("timestamp", "")) >= cutoff] if runs else []

    periods: dict[str, dict] = {}
    for run in runs:
        ts = run.get("timestamp", "")
        day = ts[:10] if ts else "unknown"
        if day not in periods:
            periods[day] = {"date": day, "total": 0, "passed": 0, "failed": 0, "errors": 0}
        periods[day]["total"] += run.get("total", 0)
        periods[day]["passed"] += run.get("passed", 0)
        periods[day]["failed"] += run.get("failed", 0)
        periods[day]["errors"] += run.get("errors", 0)

    trend_data = []
    for day in sorted(periods):
        p = periods[day]
        pass_rate = p["passed"] / p["total"] if p["total"] > 0 else 0.0
        trend_data.append({
            "date": day,
            "total": p["total"],
            "passed": p["passed"],
            "failed": p["failed"],
            "errors": p["errors"],
            "pass_rate": round(pass_rate, 4),
        })

    return {"trends": trend_data, "total_runs": len(runs)}


def _parse_iso(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


_server: BaseMcpServer | None = None


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("results-store")

    srv.tool(
        "save_result",
        description="Save an evaluation result to persistent storage. Returns a run_id.",
        input_schema={
            "type": "object",
            "properties": {
                "report": {"type": "object", "description": "Evaluation report dict"},
                "spec_path": {"type": "string", "description": "Optional spec file path"},
            },
            "required": ["report"],
        },
    )(save_result)

    srv.tool(
        "list_runs",
        description="List past evaluation runs, with optional limit and spec name filter",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of runs to return"},
                "spec_name": {"type": "string", "description": "Filter by spec name"},
            },
        },
    )(list_runs)

    srv.tool(
        "get_run",
        description="Get full details of a specific evaluation run by run_id",
        input_schema={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Run ID from save_result"},
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
                "id2": {"type": "string", "description": "Second run ID"},
            },
            "required": ["id1", "id2"],
        },
    )(compare_runs)

    srv.tool(
        "get_trends",
        description="Get pass rate trends over time, optionally filtered by spec and time window",
        input_schema={
            "type": "object",
            "properties": {
                "spec_name": {"type": "string", "description": "Filter by spec name"},
                "days": {"type": "integer", "description": "Number of days of history to include"},
            },
        },
    )(get_trends)

    _server = srv
    return srv


def main() -> None:
    import asyncio
    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
