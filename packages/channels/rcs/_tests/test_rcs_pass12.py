"""Pass12 RCS channel tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest
from loop_channels_core import OutboundFrame, OutboundFrameKind
from loop_channels_rcs import (
    RcsAdapter,
    RcsBrandProfile,
    RcsCardAction,
    RcsConnectFlow,
    RcsRichCard,
    RcsSuggestion,
    render_rich_card,
)

WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")
AGENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000003")


def test_rcs_inbound_text_and_receipt_are_lifted() -> None:
    adapter = RcsAdapter(_FakeRcsTransport())
    event, receipt = adapter.inbound(
        {
            "senderPhoneNumber": "+15551110000",
            "text": "hello",
            "messageId": "rcs-1",
        },
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert receipt is None
    assert event is not None
    assert event.user_id == "+15551110000"
    assert event.text == "hello"

    receipt_event, parsed_receipt = adapter.inbound(
        {"receipt": {"messageId": "rcs-2", "status": "READ", "eventTimeMs": 10}},
        workspace_id=WORKSPACE_ID,
        agent_id=AGENT_ID,
        conversation_id=CONVERSATION_ID,
    )
    assert receipt_event is None
    assert parsed_receipt is not None
    assert parsed_receipt.status == "READ"


def test_rcs_rich_card_renderer_and_send() -> None:
    transport = _FakeRcsTransport()
    adapter = RcsAdapter(transport)
    card = RcsRichCard(
        title="Choose",
        description="Pick an option",
        image_url="https://cdn.example/card.png",
        suggestions=(
            RcsSuggestion(text="Yes", payload="yes"),
            RcsSuggestion(text="Open", action=RcsCardAction.OPEN_URL, payload="https://example.com"),
        ),
    )
    payload = render_rich_card(card)
    assert "richCard" in payload
    assert len(payload["suggestions"]) == 2  # type: ignore[arg-type]

    message_id = adapter.send_frame(
        OutboundFrame(
            conversation_id=CONVERSATION_ID,
            kind=OutboundFrameKind.AGENT_MESSAGE,
            text="ignored because card wins",
            sequence=1,
        ),
        msisdn="+15551110000",
        card=card,
    )
    assert message_id == "rcs-out-1"
    assert "richCard" in transport.sent[0][1]


def test_rcs_connect_flow_verifies_brand_and_configures_webhook() -> None:
    provisioner = _FakeRcsProvisioner()
    result = RcsConnectFlow(provisioner).connect(
        RcsBrandProfile(
            workspace_id="ws",
            brand_id="brand-1",
            display_name="Loop",
            agent_id="agent-1",
            webhook_base_url="https://loop.example",
        )
    )
    assert result.ready
    assert result.webhook_url == "https://loop.example/channels/rcs/webhook"
    assert provisioner.configured == ("agent-1", "https://loop.example/channels/rcs/webhook")


def test_rcs_connect_rejects_non_https_webhook() -> None:
    with pytest.raises(ValueError):
        RcsConnectFlow(_FakeRcsProvisioner()).connect(
            RcsBrandProfile(
                workspace_id="ws",
                brand_id="brand-1",
                display_name="Loop",
                agent_id="agent-1",
                webhook_base_url="http://loop.local",
            )
        )


@dataclass(slots=True)
class _FakeRcsTransport:
    sent: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def send(self, *, msisdn: str, payload: dict[str, object]) -> str:
        self.sent.append((msisdn, payload))
        return f"rcs-out-{len(self.sent)}"


@dataclass(slots=True)
class _FakeRcsProvisioner:
    configured: tuple[str, str] | None = None

    def verify_brand(self, profile: RcsBrandProfile) -> str:
        assert profile.brand_id == "brand-1"
        return "verified"

    def configure_webhook(self, *, agent_id: str, webhook_url: str) -> None:
        self.configured = (agent_id, webhook_url)
