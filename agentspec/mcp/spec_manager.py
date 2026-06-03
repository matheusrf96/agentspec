from __future__ import annotations

import os

import yaml

from agentspec.mcp.protocol import BaseMcpServer
from agentspec.spec import Spec

TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_specs": "List spec files in a directory (default: current working directory)",
    "read_spec": "Parse and return a spec file as a structured JSON object",
    "validate_spec": "Validate a spec file without running it, "
    "returns valid flag and any errors",
    "create_spec": "Generate a new spec YAML file with the given name and model",
    "add_test": "Add a test case to an existing spec file",
    "add_assertion": "Add an assertion to a test case within a spec file",
    "remove_test": "Remove a test case from a spec file by name",
    "remove_assertion": "Remove an assertion from a test case by index",
}

INPUT_SCHEMAS: dict[str, dict] = {
    "list_specs": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to scan for spec files",
            },
        },
    },
    "read_spec": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the spec YAML file"},
        },
        "required": ["path"],
    },
    "validate_spec": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the spec YAML file"},
        },
        "required": ["path"],
    },
    "create_spec": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Spec name"},
            "output": {"type": "string", "description": "Output file path"},
            "model": {
                "type": "string",
                "description": "Model name (default: deepseek-v4-pro)",
            },
            "system_prompt": {
                "type": "string",
                "description": "System prompt for the agent",
            },
        },
        "required": ["name", "output"],
    },
    "add_test": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "description": "Path to the spec file"},
            "name": {"type": "string", "description": "Test case name"},
            "prompt": {"type": "string", "description": "Input prompt for the test"},
        },
        "required": ["spec_path", "name", "prompt"],
    },
    "add_assertion": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "description": "Path to the spec file"},
            "test_name": {"type": "string", "description": "Name of the test case"},
            "type": {"type": "string", "description": "Assertion type"},
            "tool_name": {"type": "string", "description": "Tool name (tool_called)"},
            "value": {
                "type": "string",
                "description": "Expected value (output_contains)",
            },
            "pattern": {"type": "string", "description": "Regex (output_matches)"},
            "max_seconds": {
                "type": "number",
                "description": "Max latency (latency_under)",
            },
            "values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Expected values (output_contains_any)",
            },
            "match": {"type": "string", "description": "Match mode: any|all"},
            "schema": {
                "type": "object",
                "description": "JSON Schema (output_json_schema)",
            },
            "case_sensitive": {"type": "boolean", "description": "Case sensitive"},
        },
        "required": ["spec_path", "test_name", "type"],
    },
    "remove_test": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "description": "Path to the spec file"},
            "test_name": {
                "type": "string",
                "description": "Name of the test case to remove",
            },
        },
        "required": ["spec_path", "test_name"],
    },
    "remove_assertion": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "description": "Path to the spec file"},
            "test_name": {"type": "string", "description": "Name of the test case"},
            "index": {"type": "integer", "description": "Assertion index (0-based)"},
        },
        "required": ["spec_path", "test_name", "index"],
    },
}


def _read_spec_raw(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _write_spec_raw(path: str, data: dict) -> None:
    with open(path, "w") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )


def list_specs(path: str | None = None) -> dict:
    search_path = path or os.getcwd()
    if not os.path.isdir(search_path):
        return {"specs": [], "error": f"Directory not found: {search_path}"}
    specs = []
    for fname in sorted(os.listdir(search_path)):
        if fname.endswith((".yaml", ".yml")):
            fpath = os.path.join(search_path, fname)
            try:
                spec = Spec.from_yaml(fpath)
                specs.append(
                    {
                        "path": os.path.abspath(fpath),
                        "name": spec.name,
                        "test_count": len(spec.tests),
                    }
                )
            except Exception:
                specs.append(
                    {
                        "path": os.path.abspath(fpath),
                        "name": fname,
                        "test_count": 0,
                    }
                )
    return {"specs": specs}


def read_spec(path: str) -> dict:
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}
    try:
        spec = Spec.from_yaml(path)
        return spec.model_dump(mode="json", exclude_none=True)
    except Exception as exc:
        return {"error": f"Failed to parse spec: {exc}"}


def validate_spec(path: str) -> dict:
    if not os.path.isfile(path):
        return {"valid": False, "errors": [f"File not found: {path}"]}
    try:
        Spec.from_yaml(path)
        return {"valid": True, "errors": []}
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)]}


def create_spec(
    name: str,
    output: str,
    model: str = "deepseek-v4-pro",
    system_prompt: str | None = None,
) -> dict:
    data = {
        "name": name,
        "model": model,
        "system_prompt": system_prompt or "You are a helpful assistant.",
        "tests": [],
    }
    _write_spec_raw(output, data)
    return {"path": os.path.abspath(output), "name": name, "test_count": 0}


def add_test(spec_path: str, name: str, prompt: str) -> dict:
    try:
        data = _read_spec_raw(spec_path)
    except FileNotFoundError:
        return {"ok": False, "error": f"File not found: {spec_path}"}
    tests = data.setdefault("tests", [])
    tests.append({"name": name, "prompt": prompt, "assertions": []})
    _write_spec_raw(spec_path, data)
    return {"ok": True, "test_name": name}


def add_assertion(spec_path: str, test_name: str, type: str, **kwargs) -> dict:
    try:
        data = _read_spec_raw(spec_path)
    except FileNotFoundError:
        return {"ok": False, "error": f"File not found: {spec_path}"}
    tests = data.get("tests", [])
    for test in tests:
        if test.get("name") == test_name:
            assertion: dict[str, object] = {"type": type}
            if type == "tool_called":
                if "tool_name" in kwargs:
                    assertion["tool_name"] = kwargs["tool_name"]
                if "args" in kwargs:
                    assertion["args"] = kwargs["args"]
            elif type in ("output_contains",):
                if "value" in kwargs:
                    assertion["value"] = kwargs["value"]
                if "case_sensitive" in kwargs:
                    assertion["case_sensitive"] = kwargs["case_sensitive"]
            elif type == "output_contains_any":
                if "values" in kwargs:
                    assertion["values"] = kwargs["values"]
                if "match" in kwargs:
                    assertion["match"] = kwargs["match"]
            elif type == "output_matches":
                if "pattern" in kwargs:
                    assertion["pattern"] = kwargs["pattern"]
            elif type == "latency_under":
                if "max_seconds" in kwargs:
                    assertion["max_seconds"] = kwargs["max_seconds"]
            elif type == "output_json_schema":
                if "schema" in kwargs:
                    assertion["schema"] = kwargs["schema"]
            test.setdefault("assertions", []).append(assertion)
            _write_spec_raw(spec_path, data)
            return {"ok": True, "assertion_index": len(test["assertions"]) - 1}
    return {"ok": False, "error": f"Test '{test_name}' not found in {spec_path}"}


def remove_test(spec_path: str, test_name: str) -> dict:
    try:
        data = _read_spec_raw(spec_path)
    except FileNotFoundError:
        return {"ok": False, "error": f"File not found: {spec_path}"}
    tests = data.get("tests", [])
    before = len(tests)
    data["tests"] = [t for t in tests if t.get("name") != test_name]
    if len(data["tests"]) == before:
        return {"ok": False, "error": f"Test '{test_name}' not found"}
    _write_spec_raw(spec_path, data)
    return {"ok": True}


def remove_assertion(spec_path: str, test_name: str, index: int) -> dict:
    try:
        data = _read_spec_raw(spec_path)
    except FileNotFoundError:
        return {"ok": False, "error": f"File not found: {spec_path}"}
    tests = data.get("tests", [])
    for test in tests:
        if test.get("name") == test_name:
            assertions = test.get("assertions", [])
            if index < 0 or index >= len(assertions):
                max_idx = len(assertions) - 1
                msg = f"Assertion index {index} out of range (0..{max_idx})"
                return {"ok": False, "error": msg}
            del assertions[index]
            _write_spec_raw(spec_path, data)
            return {"ok": True}
    return {"ok": False, "error": f"Test '{test_name}' not found"}


_server: BaseMcpServer | None = None


def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("spec-manager")

    for name in (
        "list_specs",
        "read_spec",
        "validate_spec",
        "create_spec",
        "add_test",
        "add_assertion",
        "remove_test",
        "remove_assertion",
    ):
        desc = TOOL_DESCRIPTIONS.get(name, "")
        schema = INPUT_SCHEMAS.get(name, {"type": "object", "properties": {}})
        func = globals()[name]
        srv.tool(name, description=desc, input_schema=schema)(func)

    _server = srv
    return srv


def main() -> None:
    import asyncio

    server = _build_server()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
