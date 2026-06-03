from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any, Callable

RECV_TIMEOUT = 0.1

_logger = logging.getLogger("mcp")


def send_message(msg: dict) -> None:
    body = json.dumps(msg, ensure_ascii=False, default=str)
    payload = f"Content-Length: {len(body)}\r\n\r\n{body}"
    __import__("sys").stdout.write(payload)
    __import__("sys").stdout.flush()


def receive_message() -> dict | None:
    import sys as _sys

    line = _sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    if not line.startswith("Content-Length:"):
        return None
    length = int(line.split(":")[1].strip())
    while True:
        hl = _sys.stdin.readline()
        if not hl or hl.strip() == "":
            break
    body = _sys.stdin.read(length)
    return json.loads(body)


class BaseMcpServer:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.server_name = name
        self.server_version = version
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}
        self._logger = logging.getLogger(f"mcp.{name}")

    def tool(
        self,
        name: str,
        description: str = "",
        input_schema: dict | None = None,
    ):
        def decorator(func: Callable) -> Callable:
            self._tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": input_schema or {"type": "object", "properties": {}},
            }
            self._handlers[name] = func
            return func

        return decorator

    def _capabilities(self) -> dict:
        return {"tools": {"listChanged": False}}

    def _send_result(self, msg_id: int | str, result: Any) -> None:
        send_message({"jsonrpc": "2.0", "id": msg_id, "result": result})

    def _send_error(self, msg_id: int | str, code: int, message: str, data: Any = None) -> None:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        send_message({"jsonrpc": "2.0", "id": msg_id, "error": err})

    async def _dispatch(self, msg: dict) -> None:
        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if msg_id is None:
            if method == "notifications/initialized":
                self._logger.info("Client initialized")
            elif method == "notifications/notified":
                pass
            return

        try:
            if method == "initialize":
                self._send_result(msg_id, {
                    "protocolVersion": "2025-03-26",
                    "capabilities": self._capabilities(),
                    "serverInfo": {"name": self.server_name, "version": self.server_version},
                })
            elif method == "ping":
                self._send_result(msg_id, {})
            elif method == "tools/list":
                self._send_result(msg_id, {"tools": list(self._tools.values())})
            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                if tool_name not in self._handlers:
                    self._send_error(msg_id, -32602, f"Unknown tool: {tool_name}")
                    return
                handler = self._handlers[tool_name]
                if inspect.iscoroutinefunction(handler):
                    result = await handler(**arguments)
                else:
                    result = handler(**arguments)
                text = json.dumps(result, ensure_ascii=False, default=str)
                self._send_result(msg_id, {
                    "content": [{"type": "text", "text": text}],
                })
            else:
                self._send_error(msg_id, -32601, f"Method not found: {method}")
        except Exception as exc:
            self._logger.exception("Error handling %s", method)
            self._send_error(msg_id, -32603, f"Internal error: {exc}")

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                msg = await loop.run_in_executor(None, receive_message)
                if msg is None:
                    break
                await self._dispatch(msg)
            except EOFError:
                break
            except (KeyboardInterrupt, asyncio.CancelledError):
                break
