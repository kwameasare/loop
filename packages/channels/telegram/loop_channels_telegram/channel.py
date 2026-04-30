"""TelegramChannel: chat-id-aware adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import ChannelDispatcher

from loop_channels_telegram.messages import to_send_message_body
from loop_channels_telegram.parser import parse_update


class TelegramConversationIndex:
    """Maps a Telegram ``chat_id`` to a stable conversation UUID."""

    def __init__(self) -> None:
        self._by_chat: dict[int, UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, chat_id: int) -> UUID:
        async with self._lock:
            existing = self._by_chat.get(chat_id)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_chat[chat_id] = new
            return new

    async def get(self, *, chat_id: int) -> UUID | None:
        async with self._lock:
            return self._by_chat.get(chat_id)


class TelegramChannel:
    """Bridges Telegram Bot API webhook updates to a dispatcher."""

    name: str = "telegram"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversations: TelegramConversationIndex | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        self._conversations = conversations or TelegramConversationIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_update(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("TelegramChannel.start() not called")

        chat_id = _peek_chat_id(payload)
        if chat_id is None:
            return []

        conversation_id = await self._conversations.get_or_create(chat_id=chat_id)
        parsed = parse_update(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if parsed is None:
            return []
        event, target_chat = parsed
        reply_to_id = (payload.get("message") or {}).get("message_id")
        reply_to = reply_to_id if isinstance(reply_to_id, int) else None

        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            body = to_send_message_body(
                frame,
                chat_id=target_chat,
                reply_to_message_id=reply_to,
            )
            if body is not None:
                out.append(body)
        return out


def _peek_chat_id(payload: dict[str, Any]) -> int | None:
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat") or {}
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    return chat_id if isinstance(chat_id, int) else None


__all__ = ["TelegramChannel", "TelegramConversationIndex"]
