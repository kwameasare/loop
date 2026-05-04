from __future__ import annotations

import hashlib
import hmac
import time
from uuid import uuid4

import pytest
from loop_channels_core import (
    OutboundFrame,
    OutboundFrameKind,
    from_async_generator,
)
from loop_channels_slack import (
    SignatureError,
    SlackChannel,
    parse_command,
    parse_event,
    to_blocks,
    verify_request,
)

# ----------------------------------------------------------------- verify


def _sign(secret: str, ts: str, body: bytes) -> str:
    base = f"v0:{ts}:".encode() + body
    digest = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_verify_request_accepts_valid_signature() -> None:
    secret = "shh"
    ts = str(int(time.time()))
    body = b'{"hello":"world"}'
    sig = _sign(secret, ts, body)
    verify_request(
        signing_secret=secret,
        headers={"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig},
        body=body,
    )


def test_verify_request_rejects_bad_signature() -> None:
    ts = str(int(time.time()))
    with pytest.raises(SignatureError):
        verify_request(
            signing_secret="shh",
            headers={
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": "v0=deadbeef",
            },
            body=b"{}",
        )


def test_verify_request_rejects_replay() -> None:
    secret = "shh"
    ts = "1000000000"
    body = b"{}"
    sig = _sign(secret, ts, body)
    with pytest.raises(SignatureError):
        verify_request(
            signing_secret=secret,
            headers={"X-Slack-Request-Timestamp": ts, "X-Slack-Signature": sig},
            body=body,
            now=2_000_000_000,
        )


def test_verify_request_rejects_missing_headers() -> None:
    with pytest.raises(SignatureError):
        verify_request(signing_secret="shh", headers={}, body=b"{}")


# ------------------------------------------------------------------ parse


def test_parse_event_message() -> None:
    payload = {
        "type": "event_callback",
        "team_id": "T1",
        "event": {
            "type": "message",
            "user": "U1",
            "text": "hi",
            "channel": "C1",
            "ts": "123.456",
        },
    }
    inbound = parse_event(
        payload,
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert inbound is not None
    assert inbound.text == "hi"
    assert inbound.user_id == "U1"
    assert inbound.metadata["slack_thread_ts"] == "123.456"


def test_parse_event_filters_bot_echo() -> None:
    payload = {
        "type": "event_callback",
        "event": {"type": "message", "bot_id": "B1", "text": "echo"},
    }
    assert (
        parse_event(
            payload,
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )
        is None
    )


def test_parse_command() -> None:
    inbound = parse_command(
        {
            "command": "/loop",
            "text": "do the thing",
            "user_id": "U1",
            "channel_id": "C1",
            "response_url": "https://slack/r/x",
        },
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert inbound.text == "do the thing"
    assert inbound.metadata["slack_command"] == "/loop"


# ----------------------------------------------------------------- blocks


def test_to_blocks_agent_message() -> None:
    f = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="hello",
        sequence=0,
    )
    out = to_blocks(f)
    assert out["text"] == "hello"
    assert out["blocks"][0]["type"] == "section"


def test_to_blocks_skips_streaming_kinds() -> None:
    for kind in (
        OutboundFrameKind.AGENT_TOKEN,
        OutboundFrameKind.TOOL_CALL_START,
        OutboundFrameKind.DONE,
    ):
        f = OutboundFrame(conversation_id=uuid4(), kind=kind, text="x", sequence=0)
        assert to_blocks(f) == {}


def test_to_blocks_error_includes_code() -> None:
    f = OutboundFrame(
        conversation_id=uuid4(),
        kind=OutboundFrameKind.ERROR,
        text="oops",
        payload={"code": "LOOP-RUNTIME-001"},
        sequence=0,
    )
    out = to_blocks(f)
    assert "LOOP-RUNTIME-001" in out["text"]


# ---------------------------------------------------------------- channel


@pytest.mark.asyncio
async def test_slack_channel_routes_to_dispatcher_and_threads() -> None:
    cid_seen: list = []
    ws, ag = uuid4(), uuid4()

    async def gen(event):
        cid_seen.append(event.conversation_id)
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text=f"echo {event.text}",
            sequence=0,
        )

    ch = SlackChannel(workspace_id=ws, agent_id=ag)
    await ch.start(from_async_generator(gen))

    payload = {
        "type": "event_callback",
        "team_id": "T1",
        "event": {
            "type": "message",
            "user": "U1",
            "text": "hi",
            "channel": "C1",
            "ts": "1.0",
        },
    }
    out = await ch.handle_event(payload)
    assert len(out) == 1
    assert out[0]["text"] == "echo hi"

    # Same thread -> same conversation_id reused.
    out2 = await ch.handle_event(payload)
    assert cid_seen[0] == cid_seen[1]
    assert len(out2) == 1


@pytest.mark.asyncio
async def test_slack_channel_command() -> None:
    async def gen(event):
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ack",
            sequence=0,
        )

    ch = SlackChannel(workspace_id=uuid4(), agent_id=uuid4())
    await ch.start(from_async_generator(gen))
    out = await ch.handle_command(
        {
            "command": "/loop",
            "text": "ping",
            "user_id": "U1",
            "team_id": "T1",
            "trigger_id": "trig-1",
        }
    )
    assert out[0]["text"] == "ack"
