"""Stdio JSON-RPC transport for talking to out-of-process MCP servers.

This is a *thin* client: it speaks the LSP-style ``Content-Length``
framing required by the MCP stdio transport and exposes ``initialize``,
``list_tools`` and ``call_tool`` helpers built on JSON-RPC 2.0. It does
**not** sandbox the child process -- that responsibility lives in
``dp-tool-host`` (S014/S028) which spawns the MCP server inside a
Firecracker microVM via Kata.

The client is asyncio-native and safe under concurrent ``call_tool``
because each request gets a unique numeric id and is awaited on a
dedicated future.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any


class McpProtocolError(RuntimeError):
    """Raised when the MCP server violates the wire protocol."""


class McpRemoteError(RuntimeError):
    """Raised when the MCP server returns a JSON-RPC error response."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"mcp[{code}]: {message}")
        self.code = code
        self.message = message
        self.data = data


def _encode_frame(payload: Mapping[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


async def _read_frame(reader: asyncio.StreamReader) -> dict[str, Any]:
    length: int | None = None
    while True:
        line = await reader.readline()
        if not line:
            raise McpProtocolError("MCP server closed stdout before sending a frame")
        if line in (b"\r\n", b"\n"):
            break
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":", 1)[1].strip())
            except ValueError as exc:
                raise McpProtocolError(f"invalid content-length header: {line!r}") from exc
    if length is None:
        raise McpProtocolError("missing Content-Length header")
    body = await reader.readexactly(length)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise McpProtocolError(f"invalid JSON body: {exc}") from exc


class StdioMcpClient:
    """Async MCP client that drives a child process over stdio.

    Typical use::

        async with StdioMcpClient.spawn(["python", "-m", "my_mcp_server"]) as cli:
            await cli.initialize()
            tools = await cli.list_tools()
            result = await cli.call_tool("lookup_order", {"order_id": "x"})

    Bring-your-own streams are supported via the constructor for tests.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        process: asyncio.subprocess.Process | None = None,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._process = process
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._closed = False

    @classmethod
    async def spawn(
        cls,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | os.PathLike[str] | None = None,
    ) -> StdioMcpClient:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=dict(env) if env is not None else None,
            cwd=cwd,
        )
        if proc.stdin is None or proc.stdout is None:
            raise McpProtocolError("failed to acquire MCP server stdio pipes")
        client = cls(proc.stdout, proc.stdin, process=proc)
        client._start_reader()
        return client

    def _start_reader(self) -> None:
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def __aenter__(self) -> StdioMcpClient:
        if self._reader_task is None:
            self._start_reader()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _reader_loop(self) -> None:
        try:
            while not self._closed:
                frame = await _read_frame(self._reader)
                rpc_id = frame.get("id")
                if rpc_id is None:
                    # Notification -- ignored for now (cancellation/progress
                    # arrive here in the full protocol).
                    continue
                fut = self._pending.pop(rpc_id, None)
                if fut is None or fut.done():
                    continue
                if "error" in frame:
                    err = frame["error"]
                    fut.set_exception(
                        McpRemoteError(err.get("code", -1), err.get("message", ""), err.get("data"))
                    )
                else:
                    fut.set_result(frame.get("result"))
        except (asyncio.IncompleteReadError, McpProtocolError) as exc:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(exc)
            self._pending.clear()

    async def _request(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        if self._closed:
            raise McpProtocolError("client is closed")
        self._next_id += 1
        rpc_id = self._next_id
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self._pending[rpc_id] = fut
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
        if params is not None:
            payload["params"] = dict(params)
        self._writer.write(_encode_frame(payload))
        await self._writer.drain()
        return await fut

    async def initialize(
        self,
        *,
        client_name: str = "loop-mcp",
        client_version: str = "0.1.0",
        protocol_version: str = "2024-11-05",
    ) -> dict[str, Any]:
        return await self._request(
            "initialize",
            {
                "protocolVersion": protocol_version,
                "clientInfo": {"name": client_name, "version": client_version},
                "capabilities": {},
            },
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._request("tools/list")
        if not isinstance(result, dict) or "tools" not in result:
            raise McpProtocolError(f"tools/list returned unexpected payload: {result!r}")
        return list(result["tools"])

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        return await self._request("tools/call", {"name": name, "arguments": dict(arguments)})

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._reader_task
        with contextlib.suppress(Exception):
            self._writer.close()
            await self._writer.wait_closed()
        if self._process is not None and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
