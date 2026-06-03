from __future__ import annotations

import subprocess
from pathlib import Path

from agentspec.mcp.protocol import BaseMcpServer

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


def _run_cmd(cmd: list[str], cwd: str | None = None) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(PROJECT_DIR),
            timeout=120,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "Command timed out after 120s"}
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": f"Command not found: {cmd[0]}"}


def run_pytest(
    path: str | None = None,
    marker: str | None = None,
    verbose: bool = False,
) -> dict:
    cmd = ["python", "-m", "pytest"]
    if path:
        cmd.append(path)
    if marker:
        cmd.extend(["-m", marker])
    if verbose:
        cmd.append("-v")
    result = _run_cmd(cmd)
    summary = _parse_pytest_summary(result["stdout"])
    return {
        "exit_code": result["exit_code"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "errors": summary["errors"],
        "output": result["stdout"] + result["stderr"],
    }


def _parse_pytest_summary(output: str) -> dict:
    passed = 0
    failed = 0
    errors = 0
    for line in output.split("\n"):
        line = line.strip()
        if " passed" in line or "passed " in line:
            import re

            m = re.search(r"(\d+)\s+passed", line)
            if m:
                passed = int(m.group(1))
        if " failed" in line:
            import re

            m = re.search(r"(\d+)\s+failed", line)
            if m:
                failed = int(m.group(1))
        if " error" in line:
            import re

            m = re.search(r"(\d+)\s+error", line)
            if m:
                errors = int(m.group(1))
    return {"passed": passed, "failed": failed, "errors": errors}


def run_ruff(path: str | None = None) -> dict:
    cmd = ["ruff", "check"]
    if path:
        cmd.append(path)
    result = _run_cmd(cmd)
    return {
        "exit_code": result["exit_code"],
        "passed": result["exit_code"] == 0,
        "output": result["stdout"] + result["stderr"],
    }


def run_all(path: str | None = None) -> dict:
    lint_result = run_ruff(path)
    test_result = run_pytest(path, verbose=True)
    return {
        "lint": lint_result,
        "tests": test_result,
    }


_server: BaseMcpServer | None = None


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("tests-runner")

    srv.tool(
        "run_pytest",
        description=(
            "Run pytest on the agentspec project with optional path and marker filters"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Test path or file to run"},
                "marker": {"type": "string", "description": "pytest marker expression"},
                "verbose": {"type": "boolean", "description": "Show verbose output"},
            },
        },
    )(run_pytest)

    srv.tool(
        "run_ruff",
        description="Run ruff linter on the agentspec project",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to lint (default: project root)",
                },
            },
        },
    )(run_ruff)

    srv.tool(
        "run_all",
        description="Run ruff linter first, then pytest. Returns both results.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to lint/test"},
            },
        },
    )(run_all)

    _server = srv
    return srv


def main() -> None:
    import asyncio

    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
