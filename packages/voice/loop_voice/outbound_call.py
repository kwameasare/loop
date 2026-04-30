"""Outbound voice calls (S381).

Implements the agent-initiated outbound call API. The API request shape is
strict-pydantic; ``to`` must be E.164. The controller delegates dialing to
an injected ``OutboundDialer`` Protocol so unit tests run without
Twilio/Telnyx, and so a workspace can be pinned to a specific carrier
adapter via control-plane config.

Idempotency is keyed on ``(workspace_id, idempotency_key)``: replays
return the original ``CallTicket`` unchanged so a retried POST does not
double-dial the destination.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def _validate_e164(value: str) -> str:
    if not _E164.match(value):
        raise ValueError(f"{value!r} is not a valid E.164 number")
    return value


class OutboundCallError(RuntimeError):
    """Outbound call request could not be placed."""


class OutboundCallRequest(BaseModel):
    """``POST /v1/voice/calls`` body."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: UUID
    agent_id: UUID
    from_number: str = Field(min_length=4, max_length=16)
    to_number: str = Field(min_length=4, max_length=16)
    idempotency_key: str = Field(min_length=1, max_length=128)
    opening_utterance: str = Field(min_length=1, max_length=1024)

    def model_post_init(self, _ctx: object) -> None:
        _validate_e164(self.from_number)
        _validate_e164(self.to_number)


class CallTicket(BaseModel):
    """The receipt returned to the caller; stable across replays."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    call_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    agent_id: UUID
    from_number: str
    to_number: str
    placed_at: datetime
    provider_call_sid: str = Field(min_length=1)


@runtime_checkable
class OutboundDialer(Protocol):
    """Carrier-specific dialer. Returns the provider's call SID."""

    async def dial(
        self,
        *,
        from_number: str,
        to_number: str,
        opening_utterance: str,
    ) -> str: ...


class OutboundCallController:
    """Idempotent outbound-call orchestrator."""

    def __init__(
        self,
        *,
        dialer: OutboundDialer,
        clock: object | None = None,
    ) -> None:
        self._dialer = dialer
        self._clock = clock
        self._tickets: dict[tuple[UUID, str], CallTicket] = {}

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()  # type: ignore[operator]
        return datetime.now(tz=UTC)

    async def place(self, request: OutboundCallRequest) -> CallTicket:
        key = (request.workspace_id, request.idempotency_key)
        if key in self._tickets:
            return self._tickets[key]
        try:
            sid = await self._dialer.dial(
                from_number=request.from_number,
                to_number=request.to_number,
                opening_utterance=request.opening_utterance,
            )
        except Exception as exc:
            raise OutboundCallError(f"carrier rejected dial: {exc}") from exc
        if not sid:
            raise OutboundCallError("carrier returned empty SID")
        ticket = CallTicket(
            workspace_id=request.workspace_id,
            agent_id=request.agent_id,
            from_number=request.from_number,
            to_number=request.to_number,
            placed_at=self._now(),
            provider_call_sid=sid,
        )
        self._tickets[key] = ticket
        return ticket


__all__ = [
    "CallTicket",
    "OutboundCallController",
    "OutboundCallError",
    "OutboundCallRequest",
    "OutboundDialer",
]
