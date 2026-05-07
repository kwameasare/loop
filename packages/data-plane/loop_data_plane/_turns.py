"""HTTP request mapping for dp-runtime turns."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

from loop.types import AgentEvent, ChannelType, ContentPart, TurnEvent
from loop_runtime import AgentConfig, TurnBudget, TurnExecutor
from loop_runtime.sse import SseEncoder, encode_done, encode_error, encode_turn_event
from pydantic import BaseModel, ConfigDict, Field, model_validator

from loop_data_plane._runtime_config import default_agent_model

logger = logging.getLogger(__name__)


class _DisconnectProbe(Protocol):
    """Anything with the same ``is_disconnected()`` shape as
    :class:`starlette.requests.Request`. We type against the protocol
    so unit tests can pass an in-memory stub instead of a real ASGI
    Request."""

    async def is_disconnected(self) -> bool: ...

__all__ = [
    "CrossRegionCalloutError",
    "RuntimeTurnRequest",
    "TurnAuthError",
    "TurnBudgetError",
    "TurnExecutionError",
    "TurnGatewayError",
    "TurnInternalError",
    "TurnRateLimitedError",
    "collect_turn",
    "enforce_residency_metadata",
    "stream_turn_sse",
]


class TurnExecutionError(RuntimeError):
    """Base class for turn-time runtime failures (vega #6).

    Each subclass below carries a stable error-code so the route layer
    can surface a structured envelope (and metrics + alerts) instead
    of mapping every failure to a generic ``LOOP-RT-501``.

    Order of specificity (most → least): auth, budget, rate-limit,
    upstream gateway, internal. The route layer should match the most
    specific subclass first.
    """

    code = "LOOP-RT-501"
    http_status = 502


class TurnAuthError(TurnExecutionError):
    """Caller's auth/identity failed during turn execution.

    Distinct from a request-time 401 because it can fire after the
    body is already accepted (e.g. expired token mid-turn for a long-
    running tool dispatch). Maps to HTTP 401 so callers can refresh.
    """

    code = "LOOP-RT-401"
    http_status = 401


class TurnBudgetError(TurnExecutionError):
    """Workspace plan / daily budget tripped mid-turn.

    Differs from rate-limit: budget is a *spend* ceiling, not a *rate*
    ceiling. The right caller behaviour is to surface a Stripe-link
    upgrade CTA, not to retry."""

    code = "LOOP-RT-402"
    http_status = 402


class TurnRateLimitedError(TurnExecutionError):
    """Workspace or agent token-bucket rejected the turn.

    Mirrors the HTTP-level rate-limit envelope (LOOP-RL-001) but at
    the turn-admission layer. Clients should back off using
    ``Retry-After``."""

    code = "LOOP-RT-403"
    http_status = 429


class TurnGatewayError(TurnExecutionError):
    """The upstream LLM gateway returned a structured failure (5xx,
    rate-limit, transport) that we couldn't recover from via failover.

    The original ``GatewayError.code`` (LOOP-GW-301/401/402) is preserved
    on the instance for telemetry — the http_status here defaults to
    502 because the hop that failed is upstream-of-us."""

    code = "LOOP-RT-404"
    http_status = 502


class TurnInternalError(TurnExecutionError):
    """Catch-all for unexpected runtime failures (bugs, panics).

    This is the only subclass that should ever leak a stack trace into
    structured logs — every other subclass means *we know what
    happened* and the message is part of the contract."""

    code = "LOOP-RT-501"
    http_status = 500


class CrossRegionCalloutError(TurnExecutionError):
    """Runtime data-residency guard (§24.5).

    Metadata-driven tool/callout previews can declare a target region before
    a turn reaches tool dispatch. If workspace_region and target_region differ,
    the data plane blocks at the boundary and surfaces the canonical
    LOOP-AC-602 code instead of letting the external call happen.
    """

    code = "LOOP-AC-602"
    http_status = 403


_STREAM_ERROR_MESSAGES: dict[str, str] = {
    "LOOP-GW-101": "Provider credentials were rejected.",
    "LOOP-GW-301": "Provider rate limit exceeded.",
    "LOOP-GW-401": "Provider request failed.",
    "LOOP-GW-402": "Provider transport failed.",
    "LOOP-RT-401": "Turn auth failed.",
    "LOOP-RT-402": "Workspace budget exceeded.",
    "LOOP-RT-403": "Turn rate limit exceeded.",
    "LOOP-RT-404": "Upstream gateway failed.",
    "LOOP-RT-501": "Turn execution failed.",
    "LOOP-AC-602": "Cross-region callout blocked by workspace residency policy.",
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


def enforce_residency_metadata(body: RuntimeTurnRequest) -> None:
    workspace_region = body.metadata.get("workspace_region")
    target_region = body.metadata.get("target_region")
    if not isinstance(workspace_region, str) or not isinstance(target_region, str):
        return
    if not workspace_region or not target_region or workspace_region == target_region:
        return
    tool_name = body.metadata.get("tool_name")
    detail = (
        "LOOP-AC-602 cross_region_blocked: "
        f"workspace_region={workspace_region} target_region={target_region}"
    )
    if isinstance(tool_name, str) and tool_name:
        detail += f" tool={tool_name}"
    raise CrossRegionCalloutError(detail)


async def stream_turn_sse(
    executor: TurnExecutor,
    body: RuntimeTurnRequest,
    request: _DisconnectProbe | None = None,
) -> AsyncIterator[bytes]:
    """Stream a turn over SSE.

    If ``request`` is provided, we poll ``request.is_disconnected()``
    on every event boundary. When the client drops the connection
    (browser closed, mobile backgrounded, gateway timeout, …) we
    ``aclose()`` the executor's async generator so it can release
    upstream provider sockets, stop spending tokens, and surface a
    structured cancellation in the audit log instead of letting
    work continue invisibly. Closes vega #4 (block-prod): cancelled
    SSE clients used to keep burning provider quota.
    """
    encoder = SseEncoder()
    turn_id = body.turn_id()
    agen: AsyncIterator[TurnEvent] | None = None
    try:
        enforce_residency_metadata(body)
        agen = executor.execute(
            body.agent(),
            body.event(),
            request_id=turn_id,
        )
        async for event in agen:
            if request is not None and await request.is_disconnected():
                logger.info(
                    "client disconnected mid-stream; cancelling turn",
                    extra={"request_id": turn_id},
                )
                # ``aclose`` raises ``GeneratorExit`` inside the
                # executor's coroutine, which propagates to the
                # provider stream and causes the underlying httpx
                # stream to be cancelled. Errors during teardown are
                # swallowed because the client is already gone.
                try:
                    await agen.aclose()
                except Exception:
                    logger.exception(
                        "executor failed to close cleanly after disconnect",
                        extra={"request_id": turn_id},
                    )
                return
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
    finally:
        # Belt-and-braces: if we exit through any path other than the
        # disconnect branch above (clean done, exception, generator
        # GC), make sure the executor's resources are released.
        with contextlib.suppress(Exception):
            if agen is not None:
                await agen.aclose()


async def collect_turn(
    executor: TurnExecutor,
    body: RuntimeTurnRequest,
) -> dict[str, Any]:
    turn_id = body.turn_id()
    enforce_residency_metadata(body)
    events: list[TurnEvent] = []
    try:
        async for event in executor.execute(
            body.agent(),
            body.event(),
            request_id=turn_id,
        ):
            events.append(event)
    except TurnExecutionError:
        raise
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
