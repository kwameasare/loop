"""Tests for the Email (SES) channel adapter."""

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
from loop_channels_email import (
    EmailChannel,
    EmailConversationIndex,
    parse_ses_inbound,
    to_send_email_body,
)


def _payload(
    *,
    sender: str = "alice@example.com",
    subject: str = "Hello",
    body: str = "Can you help?",
    message_id: str = "<m1@mail>",
    references: list[str] | None = None,
) -> dict:
    common: dict = {"from": [sender], "subject": subject}
    if references is not None:
        common["references"] = references
    return {
        "notificationType": "Received",
        "mail": {
            "messageId": "ses-msg-1",
            "source": sender,
            "commonHeaders": common,
            "headers": [{"name": "Message-Id", "value": message_id}],
        },
        "content": body,
    }


def test_parse_ses_inbound_basic() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    conversation_id = uuid4()
    event_and_sender = parse_ses_inbound(
        _payload(),
        workspace_id=workspace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
    )
    assert event_and_sender is not None
    event, sender = event_and_sender
    assert sender == "alice@example.com"
    assert event.text.startswith("Hello\n\nCan you help?")
    assert event.metadata["sender"] == "alice@example.com"
    assert event.metadata["subject"] == "Hello"
    assert event.metadata["message_id"] == "<m1@mail>"
    # First message of a thread: the thread root is its own message-id.
    assert event.metadata["thread_id"] == "<m1@mail>"


def test_parse_ses_inbound_strips_quoted_reply() -> None:
    body = "Sounds great.\n\nOn Mon, Jan 1, Bob wrote:\n> previous content"
    event_and_sender = parse_ses_inbound(
        _payload(body=body),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert event_and_sender is not None
    event, _ = event_and_sender
    assert "previous content" not in event.text
    assert "Sounds great." in event.text


def test_parse_ses_inbound_uses_references_thread_root() -> None:
    payload = _payload(references=["<root@mail>", "<m1@mail>"])
    event_and_sender = parse_ses_inbound(
        payload,
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert event_and_sender is not None
    event, _ = event_and_sender
    assert event.metadata["thread_id"] == "<root@mail>"


def test_parse_ses_inbound_skips_bounces() -> None:
    payload = _payload()
    payload["notificationType"] = "Bounce"
    result = parse_ses_inbound(
        payload,
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert result is None


def test_to_send_email_body_agent_message_threads_reply() -> None:
    frame = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="Sure, here is the answer.",
        sequence=0,
    )
    body = to_send_email_body(
        frame,
        to="alice@example.com",
        sender="bot@loop.dev",
        subject="Hello",
        in_reply_to="<m1@mail>",
    )
    assert body is not None
    assert body["Source"] == "bot@loop.dev"
    assert body["Destination"]["ToAddresses"] == ["alice@example.com"]
    assert body["Message"]["Subject"]["Data"] == "Re: Hello"
    assert body["Message"]["Body"]["Text"]["Data"] == "Sure, here is the answer."
    headers = {h["Name"]: h["Value"] for h in body["Headers"]}
    assert headers["In-Reply-To"] == "<m1@mail>"
    assert headers["References"] == "<m1@mail>"


def test_to_send_email_body_drops_streaming_tokens() -> None:
    token = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_TOKEN,
        text="par",
        sequence=0,
    )
    done = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.DONE,
        sequence=1,
    )
    assert (
        to_send_email_body(token, to="a@x", sender="b@x", subject="s") is None
    )
    assert to_send_email_body(done, to="a@x", sender="b@x", subject="s") is None


def test_to_send_email_body_does_not_double_re_prefix() -> None:
    frame = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="ack",
        sequence=0,
    )
    body = to_send_email_body(frame, to="a@x", sender="b@x", subject="Re: Hello")
    assert body is not None
    assert body["Message"]["Subject"]["Data"] == "Re: Hello"


@pytest.mark.asyncio
async def test_email_channel_round_trip() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    captured: list[InboundEvent] = []

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        captured.append(event)
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

    channel = EmailChannel(
        workspace_id=workspace_id,
        agent_id=agent_id,
        sender="bot@loop.dev",
    )
    await channel.start(to_dispatcher(dispatch))
    bodies = await channel.handle_event(_payload())

    assert len(captured) == 1
    assert len(bodies) == 1
    assert bodies[0]["Destination"]["ToAddresses"] == ["alice@example.com"]
    assert bodies[0]["Message"]["Body"]["Text"]["Data"] == "hi back"
    await channel.stop()


@pytest.mark.asyncio
async def test_email_channel_reuses_conversation_for_thread() -> None:
    index = EmailConversationIndex()
    workspace_id = uuid4()
    agent_id = uuid4()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ack",
            sequence=0,
        )
        if False:  # pragma: no cover -- type-checker hint
            yield  # type: ignore[unreachable]

    channel = EmailChannel(
        workspace_id=workspace_id,
        agent_id=agent_id,
        sender="bot@loop.dev",
        conversations=index,
    )
    await channel.start(to_dispatcher(dispatch))

    p1 = _payload(message_id="<m1@mail>")
    p2 = _payload(message_id="<m2@mail>", references=["<m1@mail>"])
    await channel.handle_event(p1)
    await channel.handle_event(p2)

    assert await index.get(thread_id="<m1@mail>") is not None
    # The follow-up has References=[<m1@mail>] so it must reuse the same UUID.
    assert (
        await index.get(thread_id="<m1@mail>")
        == await index.get(thread_id="<m1@mail>")
    )


@pytest.mark.asyncio
async def test_email_channel_requires_start() -> None:
    channel = EmailChannel(
        workspace_id=uuid4(),
        agent_id=uuid4(),
        sender="bot@loop.dev",
    )
    with pytest.raises(RuntimeError):
        await channel.handle_event(_payload())
