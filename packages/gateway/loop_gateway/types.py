"""Wire types for the gateway: requests, streaming events, provider protocol.

Public, strict, frozen pydantic models. The runtime depends on these so any
change is a wire-compat decision (see ADR-022).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["system", "user", "assistant", "tool"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class GatewayMessage(_StrictModel):
    role: Role
    content: str


class GatewayRequest(_StrictModel):
    """A single LLM call. ``request_id`` keys the idempotency cache (ADR-022)."""

    request_id: str
    workspace_id: str
    model: str
    messages: tuple[GatewayMessage, ...]
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
    cost_disclosed_markup_pct: float = 5.0
    cached: bool = False


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
