"""End-to-end exercise of :mod:`loop_mcp.transport` over a socket pair.

We use ``socket.socketpair()`` + ``asyncio.open_connection`` to wire a
client and a stub server through real OS pipes. That avoids the
flow-control footguns of hand-rolled in-memory transports while still
running fully in-process.
"""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

import pytest
from loop_mcp.transport import McpRemoteError, StdioMcpClient


def _frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


async def _read_one_request(reader: asyncio.StreamReader) -> dict[str, Any]:
    length = 0
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n"):
            break
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    body = await reader.readexactly(length)
    return json.loads(body)


async def _make_pair() -> tuple[StdioMcpClient, asyncio.StreamReader, asyncio.StreamWriter]:
    """Wire a duplex socket pair into a client + raw server-side streams."""

    cs, ss = socket.socketpair()
    cs.setblocking(False)
    ss.setblocking(False)
    client_reader, client_writer = await asyncio.open_connection(sock=cs)
    server_reader, server_writer = await asyncio.open_connection(sock=ss)
    client = StdioMcpClient(client_reader, client_writer)
    return client, server_reader, server_writer


async def _serve_one(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    response: dict[str, Any],
) -> dict[str, Any]:
    request = await _read_one_request(reader)
    payload = {"jsonrpc": "2.0", "id": request["id"], **response}
    writer.write(_frame(payload))
    await writer.drain()
    return request


async def test_initialize_round_trip() -> None:
    client, sr, sw = await _make_pair()
    async with client:
        server_task = asyncio.create_task(
            _serve_one(sr, sw, {"result": {"protocolVersion": "2024-11-05"}})
        )
        result = await client.initialize()
        request = await server_task
        assert request["method"] == "initialize"
        assert request["params"]["clientInfo"]["name"] == "loop-mcp"
        assert result == {"protocolVersion": "2024-11-05"}


async def test_list_tools_returns_tools_array() -> None:
    client, sr, sw = await _make_pair()
    async with client:
        tools_payload = [
            {
                "name": "lookup",
                "description": "Look up an order.",
                "inputSchema": {"type": "object"},
            }
        ]
        server_task = asyncio.create_task(_serve_one(sr, sw, {"result": {"tools": tools_payload}}))
        result = await client.list_tools()
        await server_task
        assert result == tools_payload


async def test_call_tool_propagates_remote_error() -> None:
    client, sr, sw = await _make_pair()
    async with client:
        server_task = asyncio.create_task(
            _serve_one(sr, sw, {"error": {"code": -32602, "message": "bad args"}})
        )
        with pytest.raises(McpRemoteError) as excinfo:
            await client.call_tool("lookup", {"order_id": "x"})
        await server_task
        assert excinfo.value.code == -32602
        assert "bad args" in str(excinfo.value)
