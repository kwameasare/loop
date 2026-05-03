"""Production websocket transport for voice providers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as websockets_connect
from websockets.exceptions import ConnectionClosedOK, WebSocketException


class VoiceWebSocketError(RuntimeError):
    """Provider websocket failed before an adapter could process frames."""


def _open_timeout_seconds() -> float:
    raw = os.getenv("LOOP_VOICE_WS_OPEN_TIMEOUT_SECONDS")
    if raw is None:
        return 10.0
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise VoiceWebSocketError("LOOP_VOICE_WS_OPEN_TIMEOUT_SECONDS must be numeric") from exc
    if timeout <= 0:
        raise VoiceWebSocketError("LOOP_VOICE_WS_OPEN_TIMEOUT_SECONDS must be > 0")
    return timeout


@dataclass(slots=True)
class WebsocketsAsyncWebSocket:
    """Adapter from ``websockets`` ClientConnection to Loop's small WS protocol."""

    connection: ClientConnection

    async def send_bytes(self, data: bytes) -> None:
        await self.connection.send(data)

    async def send_text(self, text: str) -> None:
        await self.connection.send(text)

    async def receive_text(self) -> str:
        try:
            message = await self.connection.recv()
        except ConnectionClosedOK:
            return ""
        except WebSocketException as exc:
            raise VoiceWebSocketError(f"websocket receive failed: {exc}") from exc
        if isinstance(message, str):
            return message
        return message.decode("utf-8")

    async def aclose(self) -> None:
        await self.connection.close()


async def open_provider_websocket(
    url: str,
    headers: Mapping[str, str],
) -> WebsocketsAsyncWebSocket:
    """Open a real provider websocket with auth headers and sane timeouts."""

    try:
        connection = await websockets_connect(
            url,
            additional_headers=dict(headers),
            open_timeout=_open_timeout_seconds(),
            max_size=None,
        )
    except (OSError, TimeoutError, WebSocketException) as exc:
        raise VoiceWebSocketError(f"websocket open failed: {exc}") from exc
    return WebsocketsAsyncWebSocket(connection=connection)


__all__ = [
    "VoiceWebSocketError",
    "WebsocketsAsyncWebSocket",
    "open_provider_websocket",
]
