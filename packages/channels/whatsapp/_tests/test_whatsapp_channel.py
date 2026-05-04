"""Tests for the WhatsApp channel adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from loop_channels_core import (
    InboundEvent,
    OutboundFrame,
    OutboundFrameKind,
    to_dispatcher,
)
from loop_channels_whatsapp import (
    ConversationIndex,
    SignatureError,
    WhatsAppChannel,
    parse_event,
    to_messages,
    verify_challenge,
    verify_signature,
)

APP_SECRET = "shh-secret"  # noqa: S105 -- test fixture
VERIFY_TOKEN = "verify-tok"  # noqa: S105 -- test fixture


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _text_payload(*, body: str = "hi", msisdn: str = "15551234567") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA",
                "changes": [
                    {
                        "value": {
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "PNID",
                            },
                            "messages": [
                                {
                                    "from": msisdn,
                                    "id": "wamid.X",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def test_verify_challenge_round_trip() -> None:
    out = verify_challenge(
        expected_token=VERIFY_TOKEN,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1234",
        },
    )
    assert out == "1234"


def test_verify_challenge_rejects_bad_token() -> None:
    with pytest.raises(SignatureError):
        verify_challenge(
            expected_token=VERIFY_TOKEN,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "1234",
            },
        )


def test_verify_signature_accepts_valid() -> None:
    body = b'{"hello":"world"}'
    verify_signature(
        app_secret=APP_SECRET,
        headers={"X-Hub-Signature-256": _sign(body)},
        body=body,
    )


def test_verify_signature_rejects_missing_header() -> None:
    with pytest.raises(SignatureError, match="missing"):
        verify_signature(app_secret=APP_SECRET, headers={}, body=b"")


def test_verify_signature_rejects_tampered_body() -> None:
    body = b'{"hello":"world"}'
    sig = _sign(body)
    with pytest.raises(SignatureError, match="mismatch"):
        verify_signature(
            app_secret=APP_SECRET,
            headers={"X-Hub-Signature-256": sig},
            body=body + b"!",
        )


def test_parse_event_text_message() -> None:
    workspace = uuid4()
    agent = uuid4()
    convo = uuid4()
    inbound = parse_event(
        _text_payload(body="hello"),
        workspace_id=workspace,
        agent_id=agent,
        conversation_id=convo,
    )
    assert inbound is not None
    assert inbound.text == "hello"
    assert inbound.user_id == "15551234567"
    assert inbound.metadata["wa_phone_number_id"] == "PNID"
    assert inbound.metadata["wa_message_type"] == "text"


def test_parse_event_image_message_uses_caption() -> None:
    payload = _text_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "15551234567",
        "id": "wamid.IMG",
        "type": "image",
        "image": {"id": "MEDIA1", "caption": "look"},
    }
    inbound = parse_event(
        payload,
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert inbound is not None
    assert inbound.text == "look"
    assert inbound.metadata["wa_media_id"] == "MEDIA1"
    assert inbound.metadata["wa_message_type"] == "image"


def test_parse_event_ignores_status_only_payloads() -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "PNID"},
                            "statuses": [{"status": "delivered"}],
                        }
                    }
                ]
            }
        ],
    }
    out = parse_event(
        payload,
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert out is None


def test_to_messages_serialises_message_handoff_error() -> None:
    convo = uuid4()
    msg = to_messages(
        OutboundFrame(
            conversation_id=convo,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="hello",
            sequence=0,
        ),
        to="15551234567",
    )
    assert msg["text"]["body"] == "hello"
    assert msg["messaging_product"] == "whatsapp"

    handoff = to_messages(
        OutboundFrame(
            conversation_id=convo,
            kind=OutboundFrameKind.HANDOFF,
            payload={"target": "human"},
            sequence=1,
        ),
        to="15551234567",
    )
    assert "human" in handoff["text"]["body"]

    err = to_messages(
        OutboundFrame(
            conversation_id=convo,
            kind=OutboundFrameKind.ERROR,
            text="boom",
            payload={"code": "RUNTIME_FAIL"},
            sequence=2,
        ),
        to="15551234567",
    )
    assert "RUNTIME_FAIL" in err["text"]["body"]

    silent = to_messages(
        OutboundFrame(
            conversation_id=convo,
            kind=OutboundFrameKind.AGENT_TOKEN,
            text="x",
            sequence=3,
        ),
        to="15551234567",
    )
    assert silent == {}


async def test_conversation_index_stable() -> None:
    idx = ConversationIndex()
    a = await idx.get_or_create(phone_number_id="P", msisdn="X")
    b = await idx.get_or_create(phone_number_id="P", msisdn="X")
    c = await idx.get_or_create(phone_number_id="P", msisdn="Y")
    assert a == b
    assert a != c


async def test_channel_dispatches_and_serialises() -> None:
    workspace = uuid4()
    agent = uuid4()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text=f"echo: {event.text}",
            sequence=0,
        )

    channel = WhatsAppChannel(workspace_id=workspace, agent_id=agent)
    await channel.start(to_dispatcher(dispatch))
    out = await channel.handle_event(_text_payload(body="ping"))
    assert len(out) == 1
    assert out[0]["text"]["body"] == "echo: ping"
    assert out[0]["to"] == "15551234567"
    await channel.stop()


async def test_channel_requires_start() -> None:
    channel = WhatsAppChannel(workspace_id=uuid4(), agent_id=uuid4())
    with pytest.raises(RuntimeError):
        await channel.handle_event(_text_payload())


async def test_channel_returns_empty_for_status_payload() -> None:
    workspace = uuid4()
    agent = uuid4()

    async def dispatch(event: InboundEvent) -> AsyncIterator[OutboundFrame]:
        yield OutboundFrame(
            conversation_id=event.conversation_id,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="never",
            sequence=0,
        )

    channel = WhatsAppChannel(workspace_id=workspace, agent_id=agent)
    await channel.start(to_dispatcher(dispatch))
    out = await channel.handle_event(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "PNID"},
                                "statuses": [{"status": "read"}],
                            }
                        }
                    ]
                }
            ],
        }
    )
    assert out == []


def test_signature_round_trip_with_canonical_body() -> None:
    payload = _text_payload()
    body = json.dumps(payload).encode("utf-8")
    # _text_payload uses a frozen 2023 timestamp; opt out of the
    # replay-window check (P0.5f) since this test is about signature
    # verification specifically. test_verify_signature_replay_window_*
    # below cover the replay path.
    verify_signature(
        app_secret=APP_SECRET,
        headers={"x-hub-signature-256": _sign(body)},
        body=body,
        verify_event_timestamps=False,
    )


def test_verify_signature_rejects_replayed_old_event() -> None:
    """P0.5f: a captured webhook with a 2-day-old `timestamp` must be
    rejected even though the HMAC signature is valid."""
    payload = _text_payload()  # contains timestamp=1700000000 (~Nov 2023)
    body = json.dumps(payload).encode("utf-8")
    with pytest.raises(SignatureError, match="replay"):
        verify_signature(
            app_secret=APP_SECRET,
            headers={"x-hub-signature-256": _sign(body)},
            body=body,
            now=1700000000 + 7200,  # 2h later — outside default 600s window
        )


def test_verify_signature_accepts_event_inside_window() -> None:
    payload = _text_payload()
    body = json.dumps(payload).encode("utf-8")
    verify_signature(
        app_secret=APP_SECRET,
        headers={"x-hub-signature-256": _sign(body)},
        body=body,
        now=1700000000 + 60,  # 1 min later — within default 600s window
    )
