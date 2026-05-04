"""Tests for the Discord channel adapter."""

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
from loop_channels_discord import (
    DiscordChannel,
    DiscordConversationIndex,
    parse_interaction,
    to_followup_body,
)


def _slash(text: str = "hello", channel_id: str = "chan-1") -> dict:
    return {
        "type": 2,
        "id": "ix-1",
        "application_id": "app-1",
        "token": "tok-1",
        "channel_id": channel_id,
        "guild_id": "guild-1",
        "member": {"user": {"id": "user-7", "username": "alice"}},
        "data": {
            "name": "ask",
            "options": [{"name": "prompt", "type": 3, "value": text}],
        },
    }


def _ping() -> dict:
    return {"type": 1, "id": "ping-1"}


def test_parse_ping_returns_none() -> None:
    assert (
        parse_interaction(
            _ping(),
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_parse_application_command() -> None:
    parsed = parse_interaction(
        _slash("hi"),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert parsed is not None
    event, channel_id = parsed
    assert channel_id == "chan-1"
    assert event.text == "hi"
    assert event.user_id == "user-7"
    assert event.metadata["channel_id"] == "chan-1"
    assert event.metadata["guild_id"] == "guild-1"
    assert event.metadata["interaction_token"] == "tok-1"
    assert event.metadata["application_id"] == "app-1"


def test_parse_message_component_uses_custom_id() -> None:
    payload = {
        "type": 3,
        "channel_id": "chan-2",
        "data": {"custom_id": "btn:retry"},
    }
    parsed = parse_interaction(
        payload, workspace_id=uuid4(), agent_id=uuid4(), conversation_id=uuid4()
    )
    assert parsed is not None
    event, _ = parsed
    assert event.text == "btn:retry"


def test_parse_command_with_no_options_uses_command_name() -> None:
    payload = _slash()
    payload["data"] = {"name": "ping"}
    parsed = parse_interaction(
        payload, workspace_id=uuid4(), agent_id=uuid4(), conversation_id=uuid4()
    )
    assert parsed is not None
    event, _ = parsed
    assert event.text == "/ping"


def test_to_followup_body_agent_message() -> None:
    frame = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="hi back",
        sequence=0,
    )
    body = to_followup_body(frame)
    assert body == {"content": "hi back"}


def test_to_followup_body_drops_streaming() -> None:
    token = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_TOKEN,
        text="t",
        sequence=0,
    )
    done = OutboundFrame(
        conversation_id=uuid4(), kind=OutboundFrameKind.DONE, sequence=1
    )
    assert to_followup_body(token) is None
    assert to_followup_body(done) is None


def test_to_followup_body_error_uses_ephemeral_flag() -> None:
    err = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.ERROR,
        text="boom",
        sequence=0,
    )
    body = to_followup_body(err)
    assert body is not None
    assert body["content"] == "boom"
    assert body["flags"] == 1 << 6


@pytest.mark.asyncio
async def test_discord_channel_round_trip() -> None:
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

    channel = DiscordChannel(workspace_id=workspace_id, agent_id=agent_id)
    await channel.start(to_dispatcher(dispatch))
    bodies = await channel.handle_interaction(_slash("hi"))
    assert len(seen) == 1
    assert bodies == [{"content": "hi back"}]
    await channel.stop()


@pytest.mark.asyncio
async def test_discord_channel_reuses_conversation_per_channel() -> None:
    index = DiscordConversationIndex()
    workspace_id = uuid4()
    agent_id = uuid4()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ok",
            sequence=0,
        )

    channel = DiscordChannel(
        workspace_id=workspace_id, agent_id=agent_id, conversations=index
    )
    await channel.start(to_dispatcher(dispatch))
    await channel.handle_interaction(_slash(channel_id="A"))
    await channel.handle_interaction(_slash(channel_id="A"))
    await channel.handle_interaction(_slash(channel_id="B"))
    cid_a = await index.get(channel_id="A")
    cid_b = await index.get(channel_id="B")
    assert cid_a is not None and cid_b is not None
    assert cid_a != cid_b


@pytest.mark.asyncio
async def test_discord_channel_requires_start() -> None:
    channel = DiscordChannel(workspace_id=uuid4(), agent_id=uuid4())
    with pytest.raises(RuntimeError):
        await channel.handle_interaction(_slash())
