"""Tests for pass10 telegram webhook (S518)."""


from __future__ import annotations

import json
from uuid import uuid4

import pytest
from loop_channels_telegram.webhook import (
    TelegramWebhookError,
    TelegramWebhookHandler,
    parse_webhook_body,
    verify_secret_token,
)


def test_verify_secret_constant_time_match():
    assert verify_secret_token(expected="abc123", received="abc123") is True
    assert verify_secret_token(expected="abc123", received="other") is False
    assert verify_secret_token(expected="abc123", received=None) is False


def test_verify_secret_rejects_empty_expected():
    with pytest.raises(TelegramWebhookError):
        verify_secret_token(expected="", received="x")


def test_parse_webhook_body_text_message():
    payload = {
        "update_id": 42,
        "message": {
            "chat": {"id": 1234},
            "from": {"id": 99, "username": "user"},
            "text": "hello",
            "date": 1,
        },
    }
    upd = parse_webhook_body(
        json.dumps(payload).encode("utf-8"),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        # P0.5f replay defense triggers on `date: 1` (epoch=1970); opt
        # out for this parser test. Replay path covered by
        # test_parse_webhook_body_rejects_replayed_event below.
        verify_event_timestamp=False,
    )
    assert upd.update_id == 42
    assert upd.chat_id == 1234
    assert upd.event is not None
    assert upd.event.text == "hello"


def test_parse_webhook_body_rejects_replayed_event():
    """P0.5f: a captured update with an old `date` is replayable
    forever unless we gate on the embedded timestamp."""
    payload = {
        "update_id": 42,
        "message": {
            "chat": {"id": 1234},
            "from": {"id": 99, "username": "user"},
            "text": "hello",
            "date": 1700000000,  # ~Nov 2023
        },
    }
    with pytest.raises(TelegramWebhookError, match="replay"):
        parse_webhook_body(
            json.dumps(payload).encode("utf-8"),
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
            now=1700000000 + 7200,  # 2h later — outside default 600s window
        )


def test_parse_webhook_body_accepts_recent_event():
    payload = {
        "update_id": 42,
        "message": {
            "chat": {"id": 1234},
            "from": {"id": 99, "username": "user"},
            "text": "hello",
            "date": 1700000000,
        },
    }
    upd = parse_webhook_body(
        json.dumps(payload).encode("utf-8"),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        now=1700000000 + 60,  # 1 minute later — well within window
    )
    assert upd.event is not None
    assert upd.event.text == "hello"


def test_parse_webhook_body_non_message_update():
    payload = {"update_id": 1, "callback_query": {"id": "x"}}
    upd = parse_webhook_body(
        json.dumps(payload).encode("utf-8"),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
    )
    assert upd.event is None
    assert upd.chat_id is None


def test_parse_webhook_body_rejects_garbage():
    with pytest.raises(TelegramWebhookError):
        parse_webhook_body(
            b"not json",
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )


def test_parse_webhook_body_rejects_missing_update_id():
    with pytest.raises(TelegramWebhookError):
        parse_webhook_body(
            b"{}",
            workspace_id=uuid4(),
            agent_id=uuid4(),
            conversation_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_handler_rejects_bad_secret():
    received: list = []

    async def on_event(event, chat_id):
        received.append((event, chat_id))

    h = TelegramWebhookHandler(
        expected_secret="s",
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        on_event=on_event,
    )
    with pytest.raises(TelegramWebhookError):
        await h.handle(body=b"{}", secret_header="wrong")


@pytest.mark.asyncio
async def test_handler_dispatches_text_message():
    received: list = []

    async def on_event(event, chat_id):
        received.append((event, chat_id))

    h = TelegramWebhookHandler(
        expected_secret="s",
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        on_event=on_event,
        # Test fixture uses date=1; opt out of replay window check.
        verify_event_timestamp=False,
    )
    payload = {
        "update_id": 7,
        "message": {
            "chat": {"id": 555},
            "from": {"id": 1},
            "text": "hi",
            "date": 1,
        },
    }
    upd = await h.handle(
        body=json.dumps(payload).encode("utf-8"), secret_header="s"
    )
    assert upd.chat_id == 555
    assert len(received) == 1
    assert received[0][1] == 555
