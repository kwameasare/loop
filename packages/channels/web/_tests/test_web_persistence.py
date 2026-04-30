"""Pass6 web-channel persistence test."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_channels_web.persistence import (
    InMemoryWebConversationStore,
    WebConversationNotFoundError,
    WebMessage,
)


@pytest.mark.asyncio
async def test_web_conversation_lifecycle() -> None:
    store = InMemoryWebConversationStore()
    ws_id = uuid4()
    ag_id = uuid4()
    conv = await store.create(
        workspace_id=ws_id, agent_id=ag_id, visitor_id="v-1", now_ms=1_000
    )
    assert conv.channel_type == "web"
    assert conv.workspace_id == ws_id
    assert conv.ended_at_ms is None
    assert conv.messages == ()

    fetched = await store.get(conv.id)
    assert fetched.id == conv.id

    appended = await store.append_message(
        conv.id, WebMessage(role="user", text="hi", created_at_ms=1_500)
    )
    assert len(appended.messages) == 1
    assert appended.messages[0].role == "user"

    ended = await store.end(conv.id, now_ms=2_000)
    assert ended.ended_at_ms == 2_000
    # idempotent
    ended2 = await store.end(conv.id, now_ms=3_000)
    assert ended2.ended_at_ms == 2_000

    with pytest.raises(ValueError, match="ended"):
        await store.append_message(
            conv.id, WebMessage(role="user", text="late", created_at_ms=4_000)
        )


@pytest.mark.asyncio
async def test_web_conversation_unknown_id() -> None:
    store = InMemoryWebConversationStore()
    with pytest.raises(WebConversationNotFoundError):
        await store.get(uuid4())


@pytest.mark.asyncio
async def test_web_conversation_requires_visitor_id() -> None:
    store = InMemoryWebConversationStore()
    with pytest.raises(ValueError, match="visitor_id"):
        await store.create(
            workspace_id=uuid4(), agent_id=uuid4(), visitor_id="", now_ms=0
        )
