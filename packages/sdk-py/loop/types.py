"""Public type definitions for the Loop SDK.

Every breaking change here requires a major SDK version bump.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


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


class ContentPart(BaseModel):
    type: Literal["text", "image", "audio", "file"]
    text: str | None = None
    url: str | None = None
    mime_type: str | None = None
    bytes_b64: str | None = None


class AgentEvent(BaseModel):
    workspace_id: UUID
    conversation_id: UUID
    user_id: str
    channel: ChannelType
    content: list[ContentPart]
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime


class AgentResponse(BaseModel):
    conversation_id: UUID
    content: list[ContentPart]
    streaming: bool = True
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list)
    end_turn: bool = True


class ToolCall(BaseModel):
    name: str
    server: str
    args: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0


class TurnEvent(BaseModel):
    """Streamed event during a turn — one of: token, tool_call, retrieval, trace, degrade, complete."""

    type: Literal["token", "tool_call", "retrieval", "trace", "degrade", "complete"]
    payload: dict[str, Any]
    ts: datetime


class Trace(BaseModel):
    turn_id: UUID
    spans: list[Span]
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    iteration_count: int = 0


class Span(BaseModel):
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
