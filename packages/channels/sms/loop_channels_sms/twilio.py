"""Twilio SMS webhook parsing and outbound transport seam."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind, OutboundFrame, OutboundFrameKind
from pydantic import BaseModel, ConfigDict, Field

from loop_channels_sms.compliance import ComplianceDecision, ComplianceKeywordHandler


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SmsOutboundMessage(_StrictModel):
    to: str
    from_number: str
    body: str = Field(min_length=1, max_length=1_600)


class TwilioSendResult(_StrictModel):
    sid: str
    status: str


class TwilioSmsClient(Protocol):
    def send_message(self, message: SmsOutboundMessage) -> TwilioSendResult: ...


class SmsInboundParser:
    def parse(
        self,
        payload: dict[str, str],
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
    ) -> InboundEvent | None:
        sender = payload.get("From", "").strip()
        body = payload.get("Body", "").strip()
        if not sender or not body:
            return None
        metadata = {
            "from": sender,
            "message_sid": payload.get("MessageSid", ""),
            "to": payload.get("To", ""),
        }
        return InboundEvent(
            workspace_id=workspace_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            kind=InboundEventKind.MESSAGE,
            user_id=sender,
            text=body,
            metadata=metadata,
        )


class TwilioSmsAdapter:
    def __init__(
        self,
        *,
        client: TwilioSmsClient,
        from_number: str,
        compliance: ComplianceKeywordHandler,
    ) -> None:
        self._client = client
        self._from_number = from_number
        self._compliance = compliance
        self._parser = SmsInboundParser()

    def inbound(
        self,
        payload: dict[str, str],
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
    ) -> tuple[InboundEvent | None, ComplianceDecision]:
        event = self._parser.parse(
            payload,
            workspace_id=workspace_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
        )
        if event is None:
            decision = self._compliance.decide(msisdn="", text="HELP")
            return None, decision
        decision = self._compliance.decide(msisdn=event.user_id or "", text=event.text)
        return (event if decision.allowed else None), decision

    def send_frame(self, frame: OutboundFrame, *, to: str) -> TwilioSendResult | None:
        if frame.kind not in {OutboundFrameKind.AGENT_MESSAGE, OutboundFrameKind.ERROR}:
            return None
        text = frame.text.strip()
        if not text:
            return None
        return self._client.send_message(
            SmsOutboundMessage(to=to, from_number=self._from_number, body=text[:1600])
        )


__all__ = [
    "SmsInboundParser",
    "SmsOutboundMessage",
    "TwilioSendResult",
    "TwilioSmsAdapter",
    "TwilioSmsClient",
]
