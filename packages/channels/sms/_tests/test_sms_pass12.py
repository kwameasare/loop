# ruff: noqa: S106
"""Pass12 SMS channel tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest
from loop_channels_core import OutboundFrame, OutboundFrameKind
from loop_channels_sms import (
    ComplianceKeywordHandler,
    InMemorySmsConsentStore,
    SmsOutboundMessage,
    TwilioConnectFlow,
    TwilioConnectRequest,
    TwilioNumberCandidate,
    TwilioSendResult,
    TwilioSmsAdapter,
)

WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")
AGENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000003")


def test_twilio_sms_inbound_respects_stop_start_help_keywords() -> None:
    store = InMemorySmsConsentStore()
    adapter = TwilioSmsAdapter(
        client=_FakeTwilioClient(),
        from_number="+15550000000",
        compliance=ComplianceKeywordHandler(store),
    )

    event, decision = adapter.inbound(
        {"From": "+15551110000", "To": "+15550000000", "Body": "STOP", "MessageSid": "SM1"},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert event is None
    assert not decision.allowed
    assert store.is_opted_out(msisdn="+15551110000")

    blocked, blocked_decision = adapter.inbound(
        {"From": "+15551110000", "To": "+15550000000", "Body": "hello", "MessageSid": "SM2"},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert blocked is None
    assert blocked_decision.response_text is not None

    start_event, start_decision = adapter.inbound(
        {"From": "+15551110000", "To": "+15550000000", "Body": "START", "MessageSid": "SM3"},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert start_event is None
    assert not start_decision.allowed
    assert not store.is_opted_out(msisdn="+15551110000")


def test_twilio_sms_adapter_parses_agent_message_and_sends() -> None:
    client = _FakeTwilioClient()
    adapter = TwilioSmsAdapter(
        client=client,
        from_number="+15550000000",
        compliance=ComplianceKeywordHandler(InMemorySmsConsentStore()),
    )
    event, decision = adapter.inbound(
        {"From": "+15551110000", "To": "+15550000000", "Body": "hello", "MessageSid": "SM4"},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert decision.allowed
    assert event is not None
    assert event.text == "hello"
    assert event.metadata["message_sid"] == "SM4"

    result = adapter.send_frame(
        OutboundFrame(
            conversation_id=CONVERSATION_ID,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="reply",
            sequence=1,
        ),
        to="+15551110000",
    )
    assert result == TwilioSendResult(sid="SM-OUT-1", status="queued")
    assert client.sent[0].body == "reply"


def test_twilio_connect_flow_configures_selected_number() -> None:
    provisioner = _FakeTwilioProvisioner()
    result = TwilioConnectFlow(provisioner).connect(
        TwilioConnectRequest(
            workspace_id="ws",
            account_sid="AC123",
            auth_token_secret_ref="twilio-token",
            webhook_base_url="https://loop.example",
            selected_number="+15551110000",
        )
    )
    assert result.ready
    assert result.inbound_webhook_url.endswith("/channels/sms/twilio/inbound")
    assert provisioner.configured == (
        "AC123",
        "+15551110000",
        "https://loop.example/channels/sms/twilio/inbound",
        "https://loop.example/channels/sms/twilio/status",
    )


def test_twilio_connect_requires_https() -> None:
    with pytest.raises(ValueError):
        TwilioConnectFlow(_FakeTwilioProvisioner()).connect(
            TwilioConnectRequest(
                workspace_id="ws",
                account_sid="AC123",
                auth_token_secret_ref="twilio-token",
                webhook_base_url="http://loop.local",
            )
        )


@dataclass(slots=True)
class _FakeTwilioClient:
    sent: list[SmsOutboundMessage] = field(default_factory=list)

    def send_message(self, message: SmsOutboundMessage) -> TwilioSendResult:
        self.sent.append(message)
        return TwilioSendResult(sid=f"SM-OUT-{len(self.sent)}", status="queued")


@dataclass(slots=True)
class _FakeTwilioProvisioner:
    configured: tuple[str, str, str, str] | None = None

    def list_numbers(self, account_sid: str) -> tuple[TwilioNumberCandidate, ...]:
        assert account_sid == "AC123"
        return (
            TwilioNumberCandidate(
                phone_number="+15551110000",
                friendly_name="Support",
                capabilities=("SMS", "MMS"),
            ),
        )

    def configure_number(
        self,
        *,
        account_sid: str,
        phone_number: str,
        inbound_webhook_url: str,
        status_callback_url: str,
    ) -> None:
        self.configured = (
            account_sid,
            phone_number,
            inbound_webhook_url,
            status_callback_url,
        )
