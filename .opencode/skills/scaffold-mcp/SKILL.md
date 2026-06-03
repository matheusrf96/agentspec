# Scaffold MCP Server

Guided workflow for creating a new MCP server.

## Steps

1. **Ask user** for: server name, list of tools (name, description, input parameters)
2. **Create server file** at `agentspec/mcp/<name>.py` using the mcp-scaffolder agent
3. **Create test file** at `tests/mcp/test_<name>.py` using the test-writer agent
4. **Register** in `.mcp.json` under `mcpServers`
5. **Verify** — Run `ruff check agentspec/mcp/<name>.py` and `python -m pytest tests/mcp/test_<name>.py -v`

## Server File Template

```python
from agentspec.mcp.protocol import BaseMcpServer

_server: BaseMcpServer | None = None

def _build_server() -> BaseMcpServer:
    global _server
    if _server is not None:
        return _server
    srv = BaseMcpServer("<name>")
    # register tools with srv.tool() decorator
    _server = srv
    return srv

def main() -> None:
    import asyncio
    server = _build_server()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
```

## .mcp.json Entry Template

```json
{
  "mcpServers": {
    "<name>": {
      "command": "python",
      "args": ["-m", "agentspec.mcp.<name>"]
    }
  }
}
```
