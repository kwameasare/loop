"""Inbound + outbound frame types shared by every channel."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class InboundEventKind(StrEnum):
    MESSAGE = "message"
    TYPING = "typing"
    SESSION_OPEN = "session_open"
    SESSION_CLOSE = "session_close"


class OutboundFrameKind(StrEnum):
    """Frame kinds emitted by the runtime over a channel.

    These align 1:1 with the SSE/Slack/WhatsApp wire formats so the
    channel adapter can serialise without an extra translation layer.
    """

    AGENT_TOKEN = "agent_token"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    HANDOFF = "handoff"
    ERROR = "error"
    DONE = "done"


class InboundEvent(_StrictModel):
    """A surface-native event lifted to a tenant-scoped envelope."""

    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    kind: InboundEventKind
    user_id: str | None = None
    text: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OutboundFrame(_StrictModel):
    """A frame produced by the runtime, bound for a channel."""

    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    kind: OutboundFrameKind
    text: str = ""
    payload: dict[str, str] = Field(default_factory=dict)
    sequence: int = Field(ge=0)


__all__ = [
    "InboundEvent",
    "InboundEventKind",
    "OutboundFrame",
    "OutboundFrameKind",
]
