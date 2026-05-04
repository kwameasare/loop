"""HTTP request mapping for dp-runtime turns."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from loop.types import AgentEvent, ChannelType, ContentPart, TurnEvent
from loop_runtime import AgentConfig, TurnBudget, TurnExecutor
from loop_runtime.sse import SseEncoder, encode_done, encode_error, encode_turn_event
from pydantic import BaseModel, ConfigDict, Field, model_validator

from loop_data_plane._runtime_config import default_agent_model

logger = logging.getLogger(__name__)

__all__ = [
    "RuntimeTurnRequest",
    "TurnExecutionError",
    "collect_turn",
    "stream_turn_sse",
]


class TurnExecutionError(RuntimeError):
    """Raised when a non-streaming turn fails before a complete event."""

    code = "LOOP-RT-501"


_STREAM_ERROR_MESSAGES: dict[str, str] = {
    "LOOP-GW-101": "Provider credentials were rejected.",
    "LOOP-GW-301": "Provider rate limit exceeded.",
    "LOOP-GW-401": "Provider request failed.",
    "LOOP-GW-402": "Provider transport failed.",
    "LOOP-RT-501": "Turn execution failed.",
}


class RuntimeTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    conversation_id: UUID
    user_id: str = Field(min_length=1)
    channel: ChannelType = ChannelType.WEB
    content: list[ContentPart] | None = None
    input: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime | None = None
    request_id: str | None = Field(default=None, min_length=1)
    agent_name: str = Field(default="default", min_length=1)
    model: str | None = Field(default=None, min_length=1)
    system_prompt: str = ""
    budget: TurnBudget | None = None

    @model_validator(mode="after")
    def require_content(self) -> RuntimeTurnRequest:
        if self.content:
            return self
        if self.input:
            return self
        raise ValueError("either content or input is required")

    def event(self) -> AgentEvent:
        content = self.content
        if content is None:
            content = [ContentPart(type="text", text=self.input)]
        return AgentEvent(
            workspace_id=self.workspace_id,
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            channel=self.channel,
            content=content,
            metadata=self.metadata,
            received_at=self.received_at or datetime.now(UTC),
        )

    def agent(self) -> AgentConfig:
        return AgentConfig(
            name=self.agent_name,
            model=self.model or default_agent_model(),
            system_prompt=self.system_prompt,
            budget=self.budget or TurnBudget(),
        )

    def turn_id(self) -> str:
        return self.request_id or str(uuid4())


async def stream_turn_sse(
    executor: TurnExecutor,
    body: RuntimeTurnRequest,
) -> AsyncIterator[bytes]:
    encoder = SseEncoder()
    turn_id = body.turn_id()
    try:
        async for event in executor.execute(
            body.agent(),
            body.event(),
            request_id=turn_id,
        ):
            yield encode_turn_event(encoder, event)
        yield encode_done(encoder, turn_id=turn_id)
    except Exception as exc:
        envelope = _stream_error_envelope(exc, request_id=turn_id)
        logger.error(
            "streaming turn failed",
            extra={"code": envelope["code"], "request_id": turn_id},
            exc_info=True,
        )
        yield encode_error(
            encoder,
            code=envelope["code"],
            message=envelope["message"],
            request_id=envelope["request_id"],
        )


async def collect_turn(
    executor: TurnExecutor,
    body: RuntimeTurnRequest,
) -> dict[str, Any]:
    turn_id = body.turn_id()
    events: list[TurnEvent] = []
    try:
        async for event in executor.execute(
            body.agent(),
            body.event(),
            request_id=turn_id,
        ):
            events.append(event)
    except Exception as exc:
        raise TurnExecutionError(str(exc)) from exc
    complete = next((event for event in reversed(events) if event.type == "complete"), None)
    text = ""
    if complete is not None:
        content_value = complete.payload.get("content")
        parts: list[object] = (
            cast(list[object], content_value) if isinstance(content_value, list) else []
        )
        for part in parts:
            if isinstance(part, dict):
                mapped = cast(Mapping[str, object], part)
                text_value = mapped.get("text")
                if isinstance(text_value, str):
                    text += text_value
    return {
        "turn_id": turn_id,
        "reply": {"text": text},
        "events": [event.model_dump(mode="json") for event in events],
    }


def _stream_error_envelope(exc: BaseException, *, request_id: str) -> dict[str, str]:
    code = getattr(exc, "code", "LOOP-RT-501")
    if not isinstance(code, str) or not code:
        code = "LOOP-RT-501"
    return {
        "code": code,
        "message": _STREAM_ERROR_MESSAGES.get(code, _STREAM_ERROR_MESSAGES["LOOP-RT-501"]),
        "request_id": request_id,
    }
