"""TeamsChannel: Bot-Framework-aware adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import ChannelDispatcher

from loop_channels_teams.messages import to_reply_activity
from loop_channels_teams.parser import parse_activity


class TeamsConversationIndex:
    """Maps a Bot Framework conversation id to a stable Loop UUID."""

    def __init__(self) -> None:
        self._by_ref: dict[str, UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, conversation_ref: str) -> UUID:
        async with self._lock:
            existing = self._by_ref.get(conversation_ref)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_ref[conversation_ref] = new
            return new

    async def get(self, *, conversation_ref: str) -> UUID | None:
        async with self._lock:
            return self._by_ref.get(conversation_ref)


class TeamsChannel:
    """Bridges a Teams Bot Framework activity to a dispatcher."""

    name: str = "teams"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversations: TeamsConversationIndex | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        self._conversations = conversations or TeamsConversationIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_activity(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("TeamsChannel.start() not called")

        conversation = payload.get("conversation") or {}
        convo_ref = conversation.get("id") if isinstance(conversation, dict) else None
        if not isinstance(convo_ref, str) or not convo_ref:
            return []

        conversation_id = await self._conversations.get_or_create(
            conversation_ref=convo_ref
        )
        parsed = parse_activity(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if parsed is None:
            return []
        event, conversation_ref_id = parsed
        reply_to = event.metadata.get("activity_id")

        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            body = to_reply_activity(
                frame,
                conversation_ref=conversation_ref_id,
                reply_to_id=reply_to,
            )
            if body is not None:
                out.append(body)
        return out


__all__ = ["TeamsChannel", "TeamsConversationIndex"]
