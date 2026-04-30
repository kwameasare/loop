"""SlackChannel: thread-aware adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import (
    ChannelDispatcher,
    InboundEvent,
)

from loop_channels_slack.blocks import to_blocks
from loop_channels_slack.parser import parse_command, parse_event


class ThreadIndex:
    """In-memory bidirectional map between Slack thread roots and
    `conversation_id` UUIDs. A persistent index lives in postgres
    later (see SCHEMA.md::slack_threads). The interface is the same."""

    def __init__(self) -> None:
        self._by_thread: dict[tuple[str, str], UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, slack_team: str, thread_ts: str) -> UUID:
        key = (slack_team, thread_ts)
        async with self._lock:
            existing = self._by_thread.get(key)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_thread[key] = new
            return new

    async def get(self, *, slack_team: str, thread_ts: str) -> UUID | None:
        async with self._lock:
            return self._by_thread.get((slack_team, thread_ts))


class SlackChannel:
    """Bridges Slack Events API + slash commands to a dispatcher.

    Like `WebChannel`, this is framework-agnostic: the caller owns the
    HTTP server. ``handle_event`` and ``handle_command`` accept already
    parsed JSON / form payloads and return a list of Slack
    ``chat.postMessage`` payloads to POST back.
    """

    name: str = "slack"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        threads: ThreadIndex | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        self._threads = threads or ThreadIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_event(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("SlackChannel.start() not called")
        team = str(payload.get("team_id", ""))
        event = payload.get("event", {})
        thread_ts = str(event.get("thread_ts") or event.get("ts", ""))
        conversation_id = await self._threads.get_or_create(slack_team=team, thread_ts=thread_ts)
        inbound = parse_event(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if inbound is None:
            return []
        return await self._collect(inbound)

    async def handle_command(self, payload: dict[str, str]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("SlackChannel.start() not called")
        team = payload.get("team_id", "")
        thread_ts = payload.get("trigger_id", "") or payload.get("user_id", "")
        conversation_id = await self._threads.get_or_create(slack_team=team, thread_ts=thread_ts)
        inbound = parse_command(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        return await self._collect(inbound)

    async def _collect(self, event: InboundEvent) -> list[dict[str, Any]]:
        assert self._dispatcher is not None
        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            block = to_blocks(frame)
            if block:
                out.append(block)
        return out


__all__ = ["SlackChannel", "ThreadIndex"]
