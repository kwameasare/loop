"""Tests for BYOC credential resolution in the Twilio SMS adapter.

Walks the full path: ``build_byoc_twilio_adapter`` calls the resolver,
validates the resolved dict, lets the caller's transport builder
construct the upstream client, and assembles a fully-wired adapter
that respects the resolved ``from_number``.

The ``ByocTwilioSmsClient`` per-call resolver covers the rotation
shape where the upstream transport gets rebuilt on each ``send_message``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import pytest
from loop_channels_core import OutboundFrame, OutboundFrameKind
from loop_channels_sms import (
    ByocCredentialsError,
    ByocTwilioSmsClient,
    ComplianceKeywordHandler,
    InMemorySmsConsentStore,
    SmsOutboundMessage,
    TwilioSendResult,
    build_byoc_twilio_adapter,
)

AGENT_ID = UUID("00000000-0000-0000-0000-000000000aaa")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000bbb")


@dataclass(slots=True)
class _FakeTwilioClient:
    sent: list[SmsOutboundMessage] = field(default_factory=list)

    def send_message(self, message: SmsOutboundMessage) -> TwilioSendResult:
        self.sent.append(message)
        return TwilioSendResult(sid=f"SM-{len(self.sent)}", status="queued")


def test_build_byoc_twilio_adapter_uses_resolved_credentials() -> None:
    resolver_calls: list[tuple[UUID, str]] = []
    transport_calls: list[dict[str, Any]] = []

    def resolver(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        resolver_calls.append((agent_id, channel_type))
        return {
            "account_sid": "AC-test-1",
            "auth_token": "secret-token",
            "from_number": "+15551112222",
        }

    fake = _FakeTwilioClient()

    def builder(creds: dict[str, Any]) -> _FakeTwilioClient:
        transport_calls.append(creds)
        return fake

    adapter = build_byoc_twilio_adapter(
        agent_id=AGENT_ID,
        resolver=resolver,
        transport_builder=builder,
        compliance=ComplianceKeywordHandler(InMemorySmsConsentStore()),
    )

    assert resolver_calls == [(AGENT_ID, "sms")]
    assert transport_calls == [
        {
            "account_sid": "AC-test-1",
            "auth_token": "secret-token",
            "from_number": "+15551112222",
        }
    ]

    result = adapter.send_frame(
        OutboundFrame(
            conversation_id=CONVERSATION_ID,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="hello",
            sequence=1,
        ),
        to="+15553334444",
    )
    assert result == TwilioSendResult(sid="SM-1", status="queued")
    sent = fake.sent[0]
    assert sent.from_number == "+15551112222"
    assert sent.to == "+15553334444"
    assert sent.body == "hello"


def test_build_byoc_twilio_adapter_rejects_missing_fields() -> None:
    def resolver(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        return {"account_sid": "AC-test", "auth_token": "secret"}  # missing from_number

    with pytest.raises(ByocCredentialsError, match="from_number"):
        build_byoc_twilio_adapter(
            agent_id=AGENT_ID,
            resolver=resolver,
            transport_builder=lambda creds: _FakeTwilioClient(),
            compliance=ComplianceKeywordHandler(InMemorySmsConsentStore()),
        )


def test_byoc_twilio_sms_client_resolves_on_each_send() -> None:
    """Per-call resolver — rotation picks up the new token on the next
    send_message without rebuilding the surrounding adapter."""
    builds: list[dict[str, Any]] = []
    fake = _FakeTwilioClient()

    def builder(creds: dict[str, Any]) -> _FakeTwilioClient:
        builds.append(creds)
        return fake

    creds_state: dict[str, Any] = {
        "account_sid": "AC-v1",
        "auth_token": "token-v1",
        "from_number": "+15550000001",
    }

    def resolver(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        return dict(creds_state)

    client = ByocTwilioSmsClient(
        agent_id=AGENT_ID,
        resolver=resolver,
        transport_builder=builder,
    )

    first = client.send_message(
        SmsOutboundMessage(to="+15554440001", from_number="+15550000001", body="hi")
    )
    assert first.sid == "SM-1"
    # Rotate: operator uploads a fresh token.
    creds_state["auth_token"] = "token-v2"
    second = client.send_message(
        SmsOutboundMessage(to="+15554440001", from_number="+15550000001", body="hi2")
    )
    assert second.sid == "SM-2"
    assert [b["auth_token"] for b in builds] == ["token-v1", "token-v2"]


def test_byoc_twilio_sms_client_rejects_missing_fields() -> None:
    def resolver(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        return {"auth_token": "secret"}  # missing both account_sid and from_number

    client = ByocTwilioSmsClient(
        agent_id=AGENT_ID,
        resolver=resolver,
        transport_builder=lambda creds: _FakeTwilioClient(),
    )
    with pytest.raises(ByocCredentialsError):
        client.send_message(
            SmsOutboundMessage(to="+1", from_number="+2", body="x")
        )
