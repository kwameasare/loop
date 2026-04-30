"""WhatsAppChannel: phone-number-aware adapter."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from loop_channels_core import (
    ChannelDispatcher,
    InboundEvent,
)

from loop_channels_whatsapp.messages import to_messages
from loop_channels_whatsapp.parser import parse_event


class ConversationIndex:
    """In-memory map between (phone_number_id, msisdn) and a stable
    ``conversation_id`` UUID. The persistent index lives in postgres
    later (see SCHEMA.md::whatsapp_conversations); the interface is
    the same."""

    def __init__(self) -> None:
        self._by_pair: dict[tuple[str, str], UUID] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        *,
        phone_number_id: str,
        msisdn: str,
    ) -> UUID:
        key = (phone_number_id, msisdn)
        async with self._lock:
            existing = self._by_pair.get(key)
            if existing is not None:
                return existing
            new = uuid4()
            self._by_pair[key] = new
            return new

    async def get(
        self,
        *,
        phone_number_id: str,
        msisdn: str,
    ) -> UUID | None:
        async with self._lock:
            return self._by_pair.get((phone_number_id, msisdn))


class WhatsAppChannel:
    """Bridges the WhatsApp Cloud API webhook to a dispatcher.

    Like ``SlackChannel``, this is framework-agnostic: the caller
    owns the HTTP server. ``handle_event`` accepts an already parsed
    JSON payload and returns the list of Cloud API request bodies to
    POST back via the runtime's HTTP transport.
    """

    name: str = "whatsapp"

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversations: ConversationIndex | None = None,
    ) -> None:
        self._workspace_id = workspace_id
        self._agent_id = agent_id
        self._conversations = conversations or ConversationIndex()
        self._dispatcher: ChannelDispatcher | None = None

    async def start(self, dispatcher: ChannelDispatcher) -> None:
        self._dispatcher = dispatcher

    async def stop(self) -> None:
        self._dispatcher = None

    async def handle_event(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dispatcher is None:
            raise RuntimeError("WhatsAppChannel.start() not called")
        pair = _extract_pair(payload)
        if pair is None:
            return []
        phone_number_id, msisdn = pair
        conversation_id = await self._conversations.get_or_create(
            phone_number_id=phone_number_id,
            msisdn=msisdn,
        )
        inbound = parse_event(
            payload,
            workspace_id=self._workspace_id,
            agent_id=self._agent_id,
            conversation_id=conversation_id,
        )
        if inbound is None:
            return []
        return await self._collect(inbound, to=msisdn)

    async def _collect(self, event: InboundEvent, *, to: str) -> list[dict[str, Any]]:
        assert self._dispatcher is not None
        out: list[dict[str, Any]] = []
        async for frame in self._dispatcher.dispatch(event):
            body = to_messages(frame, to=to)
            if body:
                out.append(body)
        return out


def _extract_pair(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Pull (phone_number_id, msisdn) from the first message.

    Returns ``None`` if either is missing -- e.g. for status-only
    callbacks the channel should ignore.
    """
    for entry in payload.get("entry") or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            if not isinstance(messages, list):
                continue
            for message in messages:
                if not isinstance(message, dict):
                    continue
                msisdn = str(message.get("from", ""))
                phone_number_id = str(value.get("metadata", {}).get("phone_number_id", ""))
                if msisdn and phone_number_id:
                    return phone_number_id, msisdn
    return None


__all__ = ["ConversationIndex", "WhatsAppChannel"]
