"""End-to-end BYOC tests across every channel's resolver seam.

Every per-channel ``byoc.py`` module exposes the same shape:

* a ``Byoc<Channel>Sender`` class (per-call rotation)
* a ``build_byoc_<channel>_sender`` factory (resolve once)
* a list of required credential fields validated against the
  resolver's payload

This module proves the contract for all of them with one
parameterised suite: happy path + rotation + missing-field rejection.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from loop_channels_core import (
    ByocCredentialsError,
    OutboundFrame,
    OutboundFrameKind,
)
from loop_channels_discord import (
    ByocDiscordSender,
    build_byoc_discord_sender,
)
from loop_channels_email import (
    ByocSmtpSender,
    build_byoc_smtp_sender,
)
from loop_channels_slack import (
    ByocSlackSender,
    build_byoc_slack_sender,
)
from loop_channels_teams import (
    ByocTeamsSender,
    build_byoc_teams_sender,
)
from loop_channels_telegram import (
    ByocTelegramSender,
    build_byoc_telegram_sender,
)
from loop_channels_whatsapp import (
    ByocWhatsAppSender,
    build_byoc_whatsapp_sender,
)


AGENT_ID = UUID("00000000-0000-0000-0000-000000000aaa")
CONVO_ID = UUID("00000000-0000-0000-0000-000000000bbb")


def _frame() -> OutboundFrame:
    return OutboundFrame(
        conversation_id=CONVO_ID,
        kind=OutboundFrameKind.AGENT_MESSAGE,
        text="hi",
        sequence=1,
    )


# (channel_type, build_fn, per_call_cls, send_kwargs, complete_creds)
_CASES = [
    (
        "whatsapp",
        build_byoc_whatsapp_sender,
        ByocWhatsAppSender,
        {"to": "+15550001111"},
        {
            "phone_number_id": "1234567890",
            "access_token": "EAAG…",
            "webhook_verify_token": "rand-string",
        },
    ),
    (
        "slack",
        build_byoc_slack_sender,
        ByocSlackSender,
        {"channel": "C123"},
        {
            "bot_token": "xoxb-1-…",
            "signing_secret": "deadbeef",
            "app_id": "A0123",
        },
    ),
    (
        "teams",
        build_byoc_teams_sender,
        ByocTeamsSender,
        {"conversation_ref": {"id": "abc"}, "reply_to_id": None},
        {
            "app_id": "11111111-2222-3333-4444-555555555555",
            "app_password": "secret",
            "tenant_id": "common",
        },
    ),
    (
        "telegram",
        build_byoc_telegram_sender,
        ByocTelegramSender,
        {"chat_id": "987654"},
        {"bot_token": "123:ABCdef"},
    ),
    (
        "discord",
        build_byoc_discord_sender,
        ByocDiscordSender,
        {"interaction_token": "abcdef"},
        {"bot_token": "MTM…", "application_id": "98765"},
    ),
    (
        "email",
        build_byoc_smtp_sender,
        ByocSmtpSender,
        {
            "to": "user@example.com",
            "sender": "noreply@acme.com",
            "subject": "test",
            "in_reply_to": None,
        },
        {
            "host": "smtp.acme.com",
            "port": "587",
            "username": "noreply@acme.com",
            "password": "smtp-pass",
        },
    ),
]


class _FakeTransport:
    """Records every send call so the test can assert on what
    creds + send-kwargs were forwarded."""

    def __init__(self) -> None:
        self.sends: list[dict[str, Any]] = []

    def send(self, **kwargs: Any) -> dict[str, Any]:
        self.sends.append(kwargs)
        return {"ok": True}


@pytest.mark.parametrize(
    ("channel_type", "build_fn", "_per_call_cls", "send_kwargs", "creds"),
    [
        (c, b, p, k, v) for c, b, p, k, v in _CASES
    ],
    ids=[c for c, *_ in _CASES],
)
def test_build_byoc_sender_resolves_and_sends(
    channel_type: str,
    build_fn: Any,
    _per_call_cls: Any,
    send_kwargs: dict[str, Any],
    creds: dict[str, Any],
) -> None:
    resolver_calls: list[tuple[UUID, str]] = []

    def resolver(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        resolver_calls.append((agent_id, channel_type))
        return creds

    fake = _FakeTransport()
    sender = build_fn(
        agent_id=AGENT_ID,
        resolver=resolver,
        transport_builder=lambda c: fake,
    )
    assert resolver_calls == [(AGENT_ID, channel_type)]
    result = sender.send(frame=_frame(), **send_kwargs)
    assert result == {"ok": True}
    assert fake.sends[0]["frame"].text == "hi"
    for k, v in send_kwargs.items():
        assert fake.sends[0][k] == v


@pytest.mark.parametrize(
    ("channel_type", "build_fn", "_per_call_cls", "_send_kwargs", "creds"),
    [
        (c, b, p, k, v) for c, b, p, k, v in _CASES
    ],
    ids=[c for c, *_ in _CASES],
)
def test_build_byoc_sender_rejects_missing_fields(
    channel_type: str,
    build_fn: Any,
    _per_call_cls: Any,
    _send_kwargs: dict[str, Any],
    creds: dict[str, Any],
) -> None:
    """Drop the first required field — factory must refuse with
    :class:`ByocCredentialsError` and the missing field name in the
    message."""
    first_key = next(iter(creds))
    broken = {k: v for k, v in creds.items() if k != first_key}

    def resolver(**kwargs: Any) -> dict[str, Any]:
        return broken

    with pytest.raises(ByocCredentialsError, match=first_key):
        build_fn(
            agent_id=AGENT_ID,
            resolver=resolver,
            transport_builder=lambda c: _FakeTransport(),
        )


@pytest.mark.parametrize(
    ("channel_type", "_build_fn", "per_call_cls", "send_kwargs", "creds"),
    [
        (c, b, p, k, v) for c, b, p, k, v in _CASES
    ],
    ids=[c for c, *_ in _CASES],
)
def test_byoc_sender_rotation_resolves_per_send(
    channel_type: str,
    _build_fn: Any,
    per_call_cls: Any,
    send_kwargs: dict[str, Any],
    creds: dict[str, Any],
) -> None:
    """Per-call sender re-resolves on every ``send`` so rotation in
    the studio reaches the next outbound message."""
    builds: list[dict[str, Any]] = []
    fake = _FakeTransport()

    def builder(c: dict[str, Any]) -> _FakeTransport:
        builds.append(c)
        return fake

    creds_state = dict(creds)

    def resolver(**kwargs: Any) -> dict[str, Any]:
        return dict(creds_state)

    sender = per_call_cls(
        agent_id=AGENT_ID,
        resolver=resolver,
        transport_builder=builder,
    )
    sender.send(frame=_frame(), **send_kwargs)
    # Rotate the first cred value.
    first_key = next(iter(creds_state))
    creds_state[first_key] = "rotated-value"
    sender.send(frame=_frame(), **send_kwargs)
    assert [b[first_key] for b in builds] == [creds[first_key], "rotated-value"]
