"""DiscordChannel: channel-id-aware adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import ChannelDispatcher, PostgresConversationIndex

from loop_channels_discord.messages import to_followup_body
from loop_channels_discord.parser import parse_interaction


class DiscordConversationIndex:
    """Maps a Discord ``channel_id`` to a stable conversation UUID."""

    def __init__(self) -> None:
        self._by_channel: dict[str, UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, channel_id: str) -> UUID:
        async with self._lock:
            existing = self._by_channel.get(channel_id)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_channel[channel_id] = new
            return new

    async def get(self, *, channel_id: str) -> UUID | None:
        async with self._lock:
            return self._by_channel.get(channel_id)


class DiscordPostgresConversationIndex:
    def __init__(self, inner: PostgresConversationIndex) -> None:
        self._inner = inner

    async def get_or_create(self, *, channel_id: str) -> UUID:
        return await self._inner.get_or_create(provider_user_id=channel_id)

    async def get(self, *, channel_id: str) -> UUID | None:
        return await self._inner.get(provider_user_id=channel_id)


class DiscordChannel:
    """Bridges Discord Interactions API webhooks to a dispatcher.

    ``handle_interaction`` returns the list of followup-message
    bodies the host should POST to
    ``https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}``;
    the host owns transport.
    """

    name: str = "discord"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversations: DiscordConversationIndex | None = None,
        conversation_index_engine: Any | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        if conversations is not None:
            self._conversations = conversations
        elif conversation_index_engine is not None:
            self._conversations = DiscordPostgresConversationIndex(
                PostgresConversationIndex(
                    conversation_index_engine,
                    workspace_id=workspace_id,
                    channel=self.name,
                )
            )
        else:
            self._conversations = DiscordConversationIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_interaction(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("DiscordChannel.start() not called")

        channel_id = payload.get("channel_id")
        if not isinstance(channel_id, str) or not channel_id:
            return []

        conversation_id = await self._conversations.get_or_create(channel_id=channel_id)
        parsed = parse_interaction(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if parsed is None:
            return []
        event, _channel_id = parsed

        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            body = to_followup_body(frame)
            if body is not None:
                out.append(body)
        return out


__all__ = ["DiscordChannel", "DiscordConversationIndex", "DiscordPostgresConversationIndex"]
