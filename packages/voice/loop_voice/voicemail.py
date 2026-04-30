"""Voicemail / no-answer fallback (S383).

When an outbound call rings out (no answer, busy, voicemail-detected)
we want to:

1. Surface the disposition to the agent runtime as a typed event,
2. Optionally play a fallback message ("Sorry I missed you, please
   text 555-..."), and
3. Schedule a callback after a configurable delay.

This module is dispatch-only: callers tell it the call disposition,
it emits a ``FallbackPlan`` describing what to do next. The runtime
acts on the plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

UTC = UTC


class CallDisposition(StrEnum):
    """Twilio-aligned call dispositions."""

    NO_ANSWER = "no-answer"
    BUSY = "busy"
    FAILED = "failed"
    CANCELED = "canceled"
    VOICEMAIL = "voicemail"
    COMPLETED = "completed"


class FallbackAction(StrEnum):
    NONE = "none"  # call connected, nothing to do
    LEAVE_VOICEMAIL = "leave_voicemail"
    SCHEDULE_CALLBACK = "schedule_callback"
    OPEN_TICKET = "open_ticket"


@dataclass(frozen=True, slots=True)
class VoicemailPolicy:
    """Per-agent fallback config."""

    leave_voicemail_on_no_answer: bool = True
    voicemail_text: str = "We tried to reach you and will follow up shortly."
    callback_delay_seconds: int = 60 * 30  # 30 min
    max_callback_attempts: int = 3
    open_ticket_after_attempts: int = 3

    def __post_init__(self) -> None:
        if self.callback_delay_seconds < 60:
            raise ValueError("callback_delay_seconds must be >=60")
        if self.max_callback_attempts < 1:
            raise ValueError("max_callback_attempts must be >=1")
        if self.open_ticket_after_attempts > self.max_callback_attempts:
            raise ValueError("open_ticket_after_attempts > max_callback_attempts")


@dataclass(frozen=True, slots=True)
class FallbackPlan:
    """What the runtime should do for one disposition + attempt."""

    plan_id: UUID
    action: FallbackAction
    voicemail_text: str | None
    callback_at_ms: int | None
    final_attempt: bool


def now_ms_default() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def plan_fallback(
    *,
    disposition: CallDisposition,
    attempt: int,
    policy: VoicemailPolicy,
    now_ms: int | None = None,
) -> FallbackPlan:
    """Decide what to do next for this disposition + attempt count."""
    if attempt < 1:
        raise ValueError("attempt must be >=1")
    if now_ms is None:
        now_ms = now_ms_default()
    if disposition is CallDisposition.COMPLETED:
        return FallbackPlan(
            plan_id=uuid4(), action=FallbackAction.NONE,
            voicemail_text=None, callback_at_ms=None, final_attempt=True,
        )
    final = attempt >= policy.max_callback_attempts
    if final:
        action = (
            FallbackAction.OPEN_TICKET
            if attempt >= policy.open_ticket_after_attempts
            else FallbackAction.NONE
        )
        return FallbackPlan(
            plan_id=uuid4(), action=action,
            voicemail_text=None, callback_at_ms=None, final_attempt=True,
        )
    if (
        disposition is CallDisposition.VOICEMAIL
        or (disposition is CallDisposition.NO_ANSWER and policy.leave_voicemail_on_no_answer)
    ):
        return FallbackPlan(
            plan_id=uuid4(),
            action=FallbackAction.LEAVE_VOICEMAIL,
            voicemail_text=policy.voicemail_text,
            callback_at_ms=now_ms + policy.callback_delay_seconds * 1000,
            final_attempt=False,
        )
    # busy / failed / canceled => just schedule a callback
    return FallbackPlan(
        plan_id=uuid4(),
        action=FallbackAction.SCHEDULE_CALLBACK,
        voicemail_text=None,
        callback_at_ms=now_ms + policy.callback_delay_seconds * 1000,
        final_attempt=False,
    )


__all__ = [
    "CallDisposition",
    "FallbackAction",
    "FallbackPlan",
    "VoicemailPolicy",
    "plan_fallback",
]
