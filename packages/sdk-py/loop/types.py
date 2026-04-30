"""Public type definitions for the Loop SDK.

These are the canonical wire types between channel adapters, the runtime,
and SDK consumers. Every breaking change here requires a major SDK version
bump (see AGENTS.md "Pydantic public type" rule).

Reference: loop_implementation/architecture/ARCHITECTURE.md §3.3.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AgentEvent",
    "AgentResponse",
    "ChannelType",
    "ContentPart",
    "Span",
    "ToolCall",
    "Trace",
    "Turn",
    "TurnEvent",
    "TurnStatus",
]


class ChannelType(StrEnum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"
    DISCORD = "discord"
    VOICE = "voice"
    WEBHOOK = "webhook"


class TurnStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


class _StrictModel(BaseModel):
    """Base for public wire types — extra fields rejected to catch typos at the boundary."""

    model_config = ConfigDict(extra="forbid", frozen=False)


class ContentPart(_StrictModel):
    type: Literal["text", "image", "audio", "file"]
    text: str | None = None
    url: str | None = None
    mime_type: str | None = None
    bytes_b64: str | None = None


class AgentEvent(_StrictModel):
    workspace_id: UUID
    conversation_id: UUID
    user_id: str
    channel: ChannelType
    content: list[ContentPart]
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime


class AgentResponse(_StrictModel):
    conversation_id: UUID
    content: list[ContentPart]
    streaming: bool = True
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list)
    end_turn: bool = True


class ToolCall(_StrictModel):
    name: str
    server: str
    args: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0


class TurnEvent(_StrictModel):
    """Streamed event during a turn.

    `type` enumerates the stream protocol — channel adapters (SSE/WS) translate
    each event 1:1 to a wire frame.
    """

    type: Literal["token", "tool_call", "retrieval", "trace", "degrade", "complete"]
    payload: dict[str, Any]
    ts: datetime


class Span(_StrictModel):
    span_id: UUID
    parent_span_id: UUID | None = None
    kind: Literal["llm", "tool", "retrieval", "memory", "channel"]
    name: str
    started_at: datetime
    ended_at: datetime | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0
    status: Literal["ok", "error", "timeout"] = "ok"
    attrs: dict[str, str] = Field(default_factory=dict)


class Trace(_StrictModel):
    turn_id: UUID
    spans: list[Span] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    iteration_count: int = 0


class Turn(_StrictModel):
    """Aggregate record of one inbound→outbound exchange.

    Persisted at end of turn for replay, evals, and audit. The runtime
    streams ``TurnEvent``s during execution; once complete, the executor
    materializes a ``Turn`` row.
    """

    turn_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    conversation_id: UUID
    agent_name: str
    event: AgentEvent
    response: AgentResponse | None = None
    status: TurnStatus = TurnStatus.PENDING
    trace: Trace | None = None
    started_at: datetime
    ended_at: datetime | None = None
    cost_usd: float = 0.0
    iteration_count: int = 0
    degrade_reason: str | None = None
