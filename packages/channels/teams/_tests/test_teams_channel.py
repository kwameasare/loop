"""Tests for the Microsoft Teams channel adapter."""

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
from loop_channels_teams import (
    TeamsChannel,
    TeamsConversationIndex,
    parse_activity,
    to_reply_activity,
)


def _activity(*, text: str = "hello", convo: str = "convo-1", activity_id: str = "act-1") -> dict:
    return {
        "type": "message",
        "id": activity_id,
        "channelId": "msteams",
        "serviceUrl": "https://smba.example/teams",
        "text": text,
        "from": {"id": "user-1", "name": "Alice"},
        "conversation": {"id": convo},
    }


def test_parse_activity_message() -> None:
    parsed = parse_activity(
        _activity(),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert parsed is not None
    event, convo = parsed
    assert convo == "convo-1"
    assert event.text == "hello"
    assert event.user_id == "user-1"
    assert event.metadata["service_url"] == "https://smba.example/teams"
    assert event.metadata["activity_id"] == "act-1"
    assert event.metadata["bot_channel"] == "msteams"


def test_parse_activity_skips_non_message() -> None:
    payload = _activity()
    payload["type"] = "conversationUpdate"
    assert (
        parse_activity(
            payload,
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_parse_activity_skips_empty_text() -> None:
    payload = _activity(text=" ")
    assert (
        parse_activity(
            payload,
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_to_reply_activity_agent_message() -> None:
    frame = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="hi back",
        sequence=0,
    )
    body = to_reply_activity(frame, conversation_ref="convo-1", reply_to_id="act-1")
    assert body == {
        "type": "message",
        "text": "hi back",
        "conversation": {"id": "convo-1"},
        "replyToId": "act-1",
    }


def test_to_reply_activity_drops_tokens_and_done() -> None:
    token = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_TOKEN,
        text="t",
        sequence=0,
    )
    done = OutboundFrame(
        conversation_id=uuid4(), kind=OutboundFrameKind.DONE, sequence=1
    )
    assert to_reply_activity(token, conversation_ref="x") is None
    assert to_reply_activity(done, conversation_ref="x") is None


@pytest.mark.asyncio
async def test_teams_channel_round_trip() -> None:
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

    channel = TeamsChannel(workspace_id=workspace_id, agent_id=agent_id)
    await channel.start(to_dispatcher(dispatch))
    bodies = await channel.handle_activity(_activity())
    assert len(seen) == 1
    assert bodies == [
        {
            "type": "message",
            "text": "hi back",
            "conversation": {"id": "convo-1"},
            "replyToId": "act-1",
        }
    ]
    await channel.stop()


@pytest.mark.asyncio
async def test_teams_channel_reuses_conversation_per_ref() -> None:
    index = TeamsConversationIndex()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ok",
            sequence=0,
        )

    channel = TeamsChannel(
        workspace_id=uuid4(), agent_id=uuid4(), conversations=index
    )
    await channel.start(to_dispatcher(dispatch))
    await channel.handle_activity(_activity(convo="X", activity_id="1"))
    await channel.handle_activity(_activity(convo="X", activity_id="2"))
    await channel.handle_activity(_activity(convo="Y", activity_id="3"))
    cid_x = await index.get(conversation_ref="X")
    cid_y = await index.get(conversation_ref="Y")
    assert cid_x is not None and cid_y is not None
    assert cid_x != cid_y


@pytest.mark.asyncio
async def test_teams_channel_requires_start() -> None:
    channel = TeamsChannel(workspace_id=uuid4(), agent_id=uuid4())
    with pytest.raises(RuntimeError):
        await channel.handle_activity(_activity())
