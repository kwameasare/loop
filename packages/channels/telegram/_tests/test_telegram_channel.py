"""Tests for the Telegram channel adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from loop_channels_core import (
    InboundEvent,
    OutboundFrame,
    OutboundFrameKind,
    to_dispatcher,
)
from loop_channels_telegram import (
    TelegramChannel,
    TelegramConversationIndex,
    parse_update,
    to_send_message_body,
)


def _update(*, chat_id: int = 42, text: str = "hello", message_id: int = 7) -> dict:
    return {
        "update_id": 100,
        "message": {
            "message_id": message_id,
            "from": {"id": 1, "username": "alice"},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


def test_parse_update_basic() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    conversation_id = uuid4()
    parsed = parse_update(
        _update(),
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
    )
    assert parsed is not None
    event, chat_id = parsed
    assert chat_id == 42
    assert event.text == "hello"
    assert event.user_id == "1"
    assert event.metadata["chat_id"] == "42"
    assert event.metadata["username"] == "alice"
    assert event.metadata["message_id"] == "7"


def test_parse_update_skips_non_text() -> None:
    payload = _update()
    payload["message"]["text"] = ""
    assert (
        parse_update(
            payload,
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_parse_update_skips_callbacks() -> None:
    payload = {"update_id": 1, "callback_query": {"id": "cb"}}
    assert (
        parse_update(
            payload,
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_to_send_message_body_agent_message() -> None:
    frame = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="hi back",
        sequence=0,
    )
    body = to_send_message_body(frame, chat_id=42, reply_to_message_id=7)
    assert body == {"chat_id": 42, "text": "hi back", "reply_to_message_id": 7}


def test_to_send_message_body_drops_tokens_and_done() -> None:
    token = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_TOKEN,
        text="hi",
        sequence=0,
    )
    done = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.DONE,
        sequence=1,
    )
    assert to_send_message_body(token, chat_id=42) is None
    assert to_send_message_body(done, chat_id=42) is None


def test_to_send_message_body_tool_markers() -> None:
    start = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.TOOL_CALL_START,
        payload={"tool": "search"},
        sequence=0,
    )
    end = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.TOOL_CALL_END,
        payload={"tool": "search"},
        sequence=1,
    )
    s_body = to_send_message_body(start, chat_id=1)
    e_body = to_send_message_body(end, chat_id=1)
    assert s_body is not None and "Calling search" in s_body["text"]
    assert e_body is not None and "Finished search" in e_body["text"]


@pytest.mark.asyncio
async def test_telegram_channel_round_trip() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    seen: list[InboundEvent] = []

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        seen.append(event)
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="hi back",
            sequence=0,
        )
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.DONE,
            sequence=1,
        )

    channel = TelegramChannel(workspace_id=workspace_id, agent_id=agent_id)
    await channel.start(to_dispatcher(dispatch))

    bodies = await channel.handle_update(_update())
    assert len(seen) == 1
    assert bodies == [{"chat_id": 42, "text": "hi back", "reply_to_message_id": 7}]
    await channel.stop()


@pytest.mark.asyncio
async def test_telegram_channel_reuses_conversation_for_chat() -> None:
    index = TelegramConversationIndex()
    workspace_id = uuid4()
    agent_id = uuid4()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ack",
            sequence=0,
        )

    channel = TelegramChannel(
        workspace_id=workspace_id, agent_id=agent_id, conversations=index
    )
    await channel.start(to_dispatcher(dispatch))

    await channel.handle_update(_update(chat_id=42, message_id=1))
    await channel.handle_update(_update(chat_id=42, message_id=2))
    await channel.handle_update(_update(chat_id=99, message_id=3))

    cid_42 = await index.get(chat_id=42)
    cid_99 = await index.get(chat_id=99)
    assert cid_42 is not None
    assert cid_99 is not None
    assert cid_42 != cid_99


@pytest.mark.asyncio
async def test_telegram_channel_requires_start() -> None:
    channel = TelegramChannel(workspace_id=uuid4(), agent_id=uuid4())
    with pytest.raises(RuntimeError):
        await channel.handle_update(_update())
