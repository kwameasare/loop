"""Wire types for the gateway: requests, streaming events, provider protocol.

Public, strict, frozen pydantic models. The runtime depends on these so any
change is a wire-compat decision (see ADR-022).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from loop_gateway.cost import DISCLOSED_MARKUP_PCT

Role = Literal["system", "user", "assistant", "tool"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ToolCall(_StrictModel):
    """A single tool invocation requested by the model in one turn.

    ``id`` is opaque and assigned by the provider; the runtime echoes it
    back on the matching ``tool`` message so the model can correlate.
    """

    id: str
    name: str
    arguments: dict[str, Any]


class GatewayMessage(_StrictModel):
    role: Role
    content: str = ""
    # Populated on assistant messages that requested tools; empty otherwise.
    tool_calls: tuple[ToolCall, ...] = ()
    # Populated only on role="tool" messages: which call this is a result for.
    tool_call_id: str | None = None
    # Optional human-readable tool name on tool result messages.
    name: str | None = None


class ToolSpec(_StrictModel):
    """JSON-Schema descriptor for a tool exposed to the model."""

    name: str
    description: str = ""
    input_schema: dict[str, Any]


class GatewayRequest(_StrictModel):
    """A single LLM call. ``request_id`` keys the idempotency cache (ADR-022)."""

    request_id: str
    workspace_id: str
    model: str
    messages: tuple[GatewayMessage, ...]
    tools: tuple[ToolSpec, ...] = ()
    temperature: float = 0.7
    max_output_tokens: int | None = None


class Usage(_StrictModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Streaming events
# ---------------------------------------------------------------------------


class GatewayDelta(_StrictModel):
    """Incremental text from the upstream model."""

    kind: Literal["delta"] = "delta"
    text: str


class GatewayDone(_StrictModel):
    """Final event: usage + cost get attached for the runtime to record."""

    kind: Literal["done"] = "done"
    usage: Usage
    cost_usd: float
    # Disclosed markup percentage. Must always equal cost.DISCLOSED_MARKUP_PCT
    # — the value is in the wire shape so consumers don't need to import the
    # cost module, but the source of truth is cost.py (ADR-012, ADR-028).
    cost_disclosed_markup_pct: float = DISCLOSED_MARKUP_PCT
    cached: bool = False
    # Tool calls the model emitted this iteration. The runtime dispatches
    # them, appends ``tool`` messages, and re-streams. Empty iff the turn
    # is finished from the model's perspective.
    tool_calls: tuple[ToolCall, ...] = ()


class GatewayError(_StrictModel):
    """Terminal failure -- the runtime degrades, never raises through this."""

    kind: Literal["error"] = "error"
    code: str
    message: str


GatewayEvent = GatewayDelta | GatewayDone | GatewayError


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class Provider(Protocol):
    """Every provider must stream and report cost. No buffered providers."""

    name: str

    def supports(self, model: str) -> bool: ...

    def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]: ...
