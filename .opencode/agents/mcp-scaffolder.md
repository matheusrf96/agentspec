---
description: Specialist for scaffolding new MCP servers for AgentSpec. Use when creating a new MCP server or registering it in .mcp.json.
mode: subagent
permission:
  edit:
    "agentspec/mcp/*.py": "allow"
    "tests/mcp/*.py": "allow"
    ".mcp.json": "allow"
  bash:
    "ruff check *": "allow"
    "python -m pytest *": "allow"
---

# mcp-scaffolder

Specialist for scaffolding new MCP servers for AgentSpec.

## Workflow

1. Read an existing MCP server (e.g., `agentspec/mcp/spec_manager.py`) as template
2. Ask user for: server name, tools list (name + description + input schema per tool)
3. Create the server file under `agentspec/mcp/<name>.py`
4. Create the test file under `tests/mcp/test_<name>.py`
5. Register in `.mcp.json`

## Server Template

```python
from agentspec.mcp.protocol import BaseMcpServer

_server: BaseMcpServer | None = None

def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server

    srv = BaseMcpServer("<name>")

    @srv.tool("tool_name", description="...", input_schema={...})
    def tool_name(param: str = "") -> dict:
        return {"result": ...}

    _server = srv
    return srv

def main() -> None:
    import asyncio
    server = _build_server()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
```

## Constraints

- Server name must match the tool category (e.g., `spec-manager`)
- All tools return dicts (JSON-RPC serializable)
- Use `BaseMcpServer` from `agentspec.mcp.protocol`
- Each file must be runnable as `python -m agentspec.mcp.<name>`
