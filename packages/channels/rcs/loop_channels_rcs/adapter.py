"""RCS webhook parser and outbound adapter."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from loop_channels_core import InboundEvent, InboundEventKind, OutboundFrame, OutboundFrameKind
from pydantic import BaseModel, ConfigDict, Field

from loop_channels_rcs.rich_cards import RcsRichCard, render_rich_card


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RcsDeliveryReceipt(_StrictModel):
    message_id: str
    status: str
    event_time_ms: int = Field(ge=0)


class RcsOutboundTransport(Protocol):
    def send(self, *, msisdn: str, payload: dict[str, object]) -> str: ...


class RcsInboundParser:
    def parse(
        self,
        payload: dict[str, object],
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
    ) -> tuple[InboundEvent | None, RcsDeliveryReceipt | None]:
        if receipt := _parse_receipt(payload):
            return None, receipt
        sender = payload.get("senderPhoneNumber")
        text = payload.get("text")
        if not isinstance(sender, str) or not isinstance(text, str) or not text.strip():
            return None, None
        metadata = {"message_id": str(payload.get("messageId", ""))}
        return (
            InboundEvent(
                workspace_id=workspace_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                kind=InboundEventKind.MESSAGE,
                user_id=sender,
                text=text.strip(),
                metadata=metadata,
            ),
            None,
        )


class RcsAdapter:
    def __init__(self, transport: RcsOutboundTransport) -> None:
        self._transport = transport
        self._parser = RcsInboundParser()

    def inbound(
        self,
        payload: dict[str, object],
        *,
        workspace_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
    ) -> tuple[InboundEvent | None, RcsDeliveryReceipt | None]:
        return self._parser.parse(
            payload,
            workspace_id=workspace_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
        )

    def send_frame(
        self,
        frame: OutboundFrame,
        *,
        msisdn: str,
        card: RcsRichCard | None = None,
    ) -> str | None:
        if card is not None:
            return self._transport.send(msisdn=msisdn, payload=render_rich_card(card))
        if frame.kind not in {OutboundFrameKind.AGENT_MESSAGE, OutboundFrameKind.ERROR}:
            return None
        text = frame.text.strip()
        if not text:
            return None
        return self._transport.send(msisdn=msisdn, payload={"text": text})


def _parse_receipt(payload: dict[str, object]) -> RcsDeliveryReceipt | None:
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        return None
    message_id = receipt.get("messageId")
    status = receipt.get("status")
    event_time_ms = receipt.get("eventTimeMs", 0)
    if not isinstance(message_id, str) or not isinstance(status, str):
        return None
    return RcsDeliveryReceipt(
        message_id=message_id,
        status=status,
        event_time_ms=int(event_time_ms),
    )


__all__ = ["RcsAdapter", "RcsDeliveryReceipt", "RcsInboundParser", "RcsOutboundTransport"]
