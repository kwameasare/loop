"""Warm websocket pool for voice ASR/TTS providers."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from loop_voice.asr_deepgram import AsyncWebSocket

Headers = Mapping[str, str]
OpenWebSocket = Callable[[str, dict[str, str]], Awaitable[AsyncWebSocket]]
ConnectionKey = tuple[str, tuple[tuple[str, str], ...]]


class ConnectionPoolError(ValueError):
    """Raised when pool timing knobs are invalid."""


def _monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def _key(url: str, headers: Headers) -> ConnectionKey:
    return (url, tuple(sorted((str(k), str(v)) for k, v in headers.items())))


def _idle_map() -> dict[ConnectionKey, _IdleSocket]:
    return {}


@dataclass(slots=True)
class _IdleSocket:
    ws: AsyncWebSocket
    last_used_ms: int


@dataclass(slots=True)
class PooledWebSocket:
    """Proxy that returns a websocket to the pool on ``aclose``."""

    pool: WarmWebSocketPool
    key: ConnectionKey
    ws: AsyncWebSocket
    _released: bool = False

    async def send_bytes(self, data: bytes) -> None:
        await self.ws.send_bytes(data)

    async def send_text(self, text: str) -> None:
        await self.ws.send_text(text)

    async def receive_text(self) -> str:
        return await self.ws.receive_text()

    async def aclose(self) -> None:
        if self._released:
            return
        self._released = True
        await self.pool.release(self.key, self.ws)


@dataclass(slots=True)
class WarmWebSocketPool:
    """Pre-handshake and reuse provider websocket sessions.

    The pool is provider-agnostic. Adapters keep receiving an ``open_ws``
    callable; production passes ``pool.open`` and can call ``prewarm``
    before the first ASR/TTS turn.
    """

    open_ws: OpenWebSocket
    idle_timeout_ms: int = 300_000
    keepalive_text: str = '{"type":"KeepAlive"}'
    now_ms: Callable[[], int] = _monotonic_ms
    _idle: dict[ConnectionKey, _IdleSocket] = field(default_factory=_idle_map)
    opened_count: int = 0
    reused_count: int = 0
    keepalive_count: int = 0
    closed_idle_count: int = 0

    def __post_init__(self) -> None:
        if self.idle_timeout_ms <= 0:
            raise ConnectionPoolError("idle_timeout_ms must be > 0")

    async def prewarm(self, url: str, headers: Headers) -> None:
        key = _key(url, headers)
        await self.close_idle()
        if key in self._idle:
            return
        self._idle[key] = _IdleSocket(
            ws=await self._open(url, headers),
            last_used_ms=self.now_ms(),
        )

    async def open(self, url: str, headers: dict[str, str]) -> PooledWebSocket:
        key = _key(url, headers)
        await self.close_idle()
        idle = self._idle.pop(key, None)
        if idle is None:
            ws = await self._open(url, headers)
        else:
            ws = idle.ws
            self.reused_count += 1
        return PooledWebSocket(pool=self, key=key, ws=ws)

    async def release(self, key: ConnectionKey, ws: AsyncWebSocket) -> None:
        previous = self._idle.get(key)
        if previous is not None and previous.ws is not ws:
            await previous.ws.aclose()
        self._idle[key] = _IdleSocket(ws=ws, last_used_ms=self.now_ms())

    async def keepalive(self) -> None:
        for key, idle in list(self._idle.items()):
            try:
                await idle.ws.send_text(self.keepalive_text)
            except Exception:
                self._idle.pop(key, None)
                await idle.ws.aclose()
            else:
                self.keepalive_count += 1

    async def close_idle(self) -> None:
        now = self.now_ms()
        for key, idle in list(self._idle.items()):
            if now - idle.last_used_ms < self.idle_timeout_ms:
                continue
            self._idle.pop(key, None)
            await idle.ws.aclose()
            self.closed_idle_count += 1

    async def aclose(self) -> None:
        for key, idle in list(self._idle.items()):
            self._idle.pop(key, None)
            await idle.ws.aclose()

    async def _open(self, url: str, headers: Headers) -> AsyncWebSocket:
        self.opened_count += 1
        return await self.open_ws(url, dict(headers))


__all__ = [
    "ConnectionPoolError",
    "PooledWebSocket",
    "WarmWebSocketPool",
]
