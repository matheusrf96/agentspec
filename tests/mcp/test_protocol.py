from __future__ import annotations

import asyncio
import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from agentspec.mcp.protocol import BaseMcpServer, receive_message, send_message


def test_send_message_contains_content_length_header(capsys):
    send_message({"jsonrpc": "2.0", "id": 1, "result": {}})
    out, _ = capsys.readouterr()
    assert "Content-Length:" in out


def test_send_message_contains_json_body(capsys):
    send_message({"jsonrpc": "2.0", "id": 42, "result": {"ok": True}})
    out, _ = capsys.readouterr()
    assert '"jsonrpc": "2.0"' in out
    assert '"id": 42' in out
    assert '"ok": true' in out


def test_send_message_respects_content_length(capsys):
    send_message({"jsonrpc": "2.0", "id": 1, "result": None})
    out, _ = capsys.readouterr()
    header_line = out.split("\r\n")[0]
    length = int(header_line.split(":")[1].strip())
    body_start = out.index("\r\n\r\n") + 4
    body = out[body_start:]
    assert length == len(body)


def test_receive_message_reads_correctly():
    data = 'Content-Length: 27\r\n\r\n{"jsonrpc": "2.0", "id": 1}'
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is not None
    assert msg["jsonrpc"] == "2.0"
    assert msg["id"] == 1


def test_receive_message_returns_none_on_empty_input():
    with patch("sys.stdin", StringIO("")):
        msg = receive_message()
    assert msg is None


def test_receive_message_handles_multiple_headers():
    data = (
        "Content-Length: 27\r\nContent-Type: application/json\r\n\r\n"
        '{"jsonrpc": "2.0", "id": 2}'
    )
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is not None
    assert msg["id"] == 2


def test_receive_message_skips_empty_first_line():
    data = '\r\nContent-Length: 25\r\n\r\n{"jsonrpc": "2.0", "id": 3}'
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is None


class TestBaseMcpServer:
    @pytest.fixture
    def server(self):
        srv = BaseMcpServer("test-server", "0.1.0")
        return srv

    @pytest.fixture
    def server_with_tool(self, server):
        @server.tool(
            "hello",
            description="Says hello",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
        )
        def hello(name: str = "world") -> dict:
            return {"greeting": f"Hello, {name}!"}

        return server

    @pytest.fixture
    def capsys_clean(self, capsys):
        capsys.readouterr()
        return capsys

    def test_tool_registration(self, server):
        @server.tool("my_tool")
        def my_tool() -> dict:
            return {"ok": True}

        assert "my_tool" in server._tools
        assert "my_tool" in server._handlers

    def test_tool_decorator_preserves_function(self, server):
        @server.tool("add")
        def add(a: int = 0, b: int = 0) -> int:
            return a + b

        assert add(2, 3) == 5

    @pytest.mark.asyncio
    async def test_dispatch_initialize(self, server, capsys_clean):
        await server._dispatch({"id": 1, "method": "initialize", "params": {}})
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert msg["id"] == 1
        assert "result" in msg
        assert msg["result"]["protocolVersion"] == "2025-03-26"
        assert msg["result"]["serverInfo"]["name"] == "test-server"

    @pytest.mark.asyncio
    async def test_dispatch_ping(self, server, capsys_clean):
        await server._dispatch({"id": 2, "method": "ping", "params": {}})
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert msg["id"] == 2
        assert msg["result"] == {}

    @pytest.mark.asyncio
    async def test_dispatch_tools_list(self, server_with_tool, capsys_clean):
        await server_with_tool._dispatch(
            {"id": 3, "method": "tools/list", "params": {}}
        )
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert msg["id"] == 3
        tools = msg["result"]["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "hello"

    @pytest.mark.asyncio
    async def test_dispatch_tools_call(self, server_with_tool, capsys_clean):
        await server_with_tool._dispatch(
            {
                "id": 4,
                "method": "tools/call",
                "params": {"name": "hello", "arguments": {"name": "Alice"}},
            }
        )
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert msg["id"] == 4
        content = json.loads(msg["result"]["content"][0]["text"])
        assert content["greeting"] == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool_returns_error(self, server, capsys_clean):
        await server._dispatch(
            {
                "id": 5,
                "method": "tools/call",
                "params": {"name": "nonexistent", "arguments": {}},
            }
        )
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert "error" in msg
        assert msg["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_dispatch_unknown_method_returns_error(self, server, capsys_clean):
        await server._dispatch({"id": 6, "method": "unknown_method", "params": {}})
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert "error" in msg
        assert msg["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_dispatch_notification_no_response(self, server, capsys_clean):
        await server._dispatch({"method": "notifications/initialized", "params": {}})
        out, _ = capsys_clean.readouterr()
        assert out == ""

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception_returns_error(self, server, capsys_clean):
        @server.tool("crash")
        def crash() -> dict:
            raise ValueError("boom")

        await server._dispatch(
            {
                "id": 7,
                "method": "tools/call",
                "params": {"name": "crash", "arguments": {}},
            }
        )
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        assert "error" in msg
        assert msg["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_dispatch_async_handler(self, server, capsys_clean):
        @server.tool("async_hello")
        async def async_hello(name: str = "world") -> dict:
            await asyncio.sleep(0.01)
            return {"greeting": f"Hi, {name}!"}

        await server._dispatch(
            {
                "id": 8,
                "method": "tools/call",
                "params": {"name": "async_hello", "arguments": {"name": "Bob"}},
            }
        )
        out, _ = capsys_clean.readouterr()
        msg = json.loads(out.split("\r\n\r\n", 1)[1])
        content = json.loads(msg["result"]["content"][0]["text"])
        assert content["greeting"] == "Hi, Bob!"

    @pytest.mark.asyncio
    async def test_run_loop_breaks_on_none_message(self, server):
        with patch("agentspec.mcp.protocol.receive_message", return_value=None):
            await server.run()

    @pytest.mark.asyncio
    async def test_run_loop_breaks_on_keyboard_interrupt(self, server):
        mock_recv = MagicMock(side_effect=[KeyboardInterrupt()])
        with patch("agentspec.mcp.protocol.receive_message", mock_recv):
            await server.run()

    def test_tool_registration_returned_decorator_uses_default_name(self, server):
        @server.tool("func1")
        def func1():
            return {"ok": True}

        assert server._tools["func1"]["name"] == "func1"

    def test_capabilities_includes_tools(self, server):
        caps = server._capabilities()
        assert "tools" in caps
        assert caps["tools"]["listChanged"] is False


class TestRawJsonMode:
    def test_raw_json_send_message(self):
        """Line 17: raw JSON mode writes just the JSON body"""
        import agentspec.mcp.protocol as proto
        from agentspec.mcp.protocol import send_message

        proto._use_raw_json = True
        try:
            send_message({"jsonrpc": "2.0", "id": 1})
            proto._use_raw_json = True
            send_message({"jsonrpc": "2.0", "id": 1})
        finally:
            proto._use_raw_json = None


def test_parse_content_length_invalid_json():
    """Lines 27-28: invalid JSON returns None"""
    data = "Content-Length: 5\r\n\r\n{bad}"
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is None


def test_receive_message_raw_json_line():
    """Lines 54-55: detect raw JSON mode from non-Content-Length line"""
    import agentspec.mcp.protocol as proto

    proto._use_raw_json = None
    data = '{"jsonrpc": "2.0", "id": 1}\n'
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is not None
    assert msg["id"] == 1
    assert proto._use_raw_json is True
    proto._use_raw_json = None


def test_receive_message_raw_json_invalid():
    """Lines 59-60: invalid JSON in raw mode returns None"""
    import agentspec.mcp.protocol as proto

    proto._use_raw_json = None
    data = "not valid json\n"
    with patch("sys.stdin", StringIO(data)):
        msg = receive_message()
    assert msg is None
    assert proto._use_raw_json is True
    proto._use_raw_json = None


class TestBaseMcpServerNotifications:
    @pytest.fixture
    def server(self):
        return BaseMcpServer("test-server")

    @pytest.mark.asyncio
    async def test_notifications_notified(self, server):
        """Lines 111-112: notifications/notified is silently handled"""
        await server._dispatch(
            {
                "id": None,
                "method": "notifications/notified",
            }
        )

    @pytest.mark.asyncio
    async def test_notifications_initialized(self, server):
        """Line 109: notifications/initialized logs but doesn't error"""
        await server._dispatch(
            {
                "id": None,
                "method": "notifications/initialized",
            }
        )

    def test__send_error_with_data(self):
        """Line 100: _send_error includes data field"""
        server = BaseMcpServer("test")
        server._send_error(1, -32603, "err", data={"detail": "info"})

    @pytest.mark.asyncio
    async def test_run_dispatch_message(self, server):
        """Line 165: run dispatches a received message"""
        import agentspec.mcp.protocol as proto

        proto._use_raw_json = True
        data = '{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n'
        with patch("sys.stdin", StringIO(data)):
            await server.run()
        proto._use_raw_json = None

    @pytest.mark.asyncio
    async def test_run_eof_error(self, server):
        """Line 167: run() handles EOFError from stdin"""
        import agentspec.mcp.protocol as proto

        old = proto._use_raw_json
        proto._use_raw_json = None
        try:
            mock_stdin = MagicMock()
            mock_stdin.readline.side_effect = EOFError()
            with patch("sys.stdin", mock_stdin):
                await server.run()
        finally:
            proto._use_raw_json = old
