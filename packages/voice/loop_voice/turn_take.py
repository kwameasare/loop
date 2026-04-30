"""Turn-taking finite state machine (S367).

Voice agents need a tiny state machine to coordinate full-duplex
audio: the agent can either be **listening** (mic open, ASR
streaming), **thinking** (LLM in flight, TTS not yet started),
**speaking** (TTS streaming to the caller), or **idle** (call
connected but no active turn). Each transition is event-driven —
``user_started_talking``, ``vad_silence``, ``llm_first_token``,
``tts_complete`` — and illegal transitions raise so we can spot
regressions before shipping a flaky barge-in experience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "IllegalTurnTakeTransition",
    "TurnTakeEvent",
    "TurnTakeFSM",
    "TurnTakeState",
]


class TurnTakeState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class TurnTakeEvent(StrEnum):
    USER_STARTED_TALKING = "user_started_talking"
    VAD_SILENCE = "vad_silence"
    LLM_FIRST_TOKEN = "llm_first_token"  # noqa: S105 -- event name, not a secret
    TTS_COMPLETE = "tts_complete"
    BARGE_IN = "barge_in"
    """User started speaking while agent was speaking — cut TTS, restart listen."""
    CALL_ENDED = "call_ended"


# Edge table: (state, event) -> next_state. Missing entries are illegal.
_TRANSITIONS: dict[tuple[TurnTakeState, TurnTakeEvent], TurnTakeState] = {
    (TurnTakeState.IDLE, TurnTakeEvent.USER_STARTED_TALKING): TurnTakeState.LISTENING,
    (TurnTakeState.IDLE, TurnTakeEvent.CALL_ENDED): TurnTakeState.IDLE,
    (TurnTakeState.LISTENING, TurnTakeEvent.VAD_SILENCE): TurnTakeState.THINKING,
    (TurnTakeState.LISTENING, TurnTakeEvent.CALL_ENDED): TurnTakeState.IDLE,
    (TurnTakeState.LISTENING, TurnTakeEvent.USER_STARTED_TALKING): TurnTakeState.LISTENING,
    (TurnTakeState.THINKING, TurnTakeEvent.LLM_FIRST_TOKEN): TurnTakeState.SPEAKING,
    (TurnTakeState.THINKING, TurnTakeEvent.CALL_ENDED): TurnTakeState.IDLE,
    (TurnTakeState.THINKING, TurnTakeEvent.BARGE_IN): TurnTakeState.LISTENING,
    (TurnTakeState.SPEAKING, TurnTakeEvent.TTS_COMPLETE): TurnTakeState.IDLE,
    (TurnTakeState.SPEAKING, TurnTakeEvent.BARGE_IN): TurnTakeState.LISTENING,
    (TurnTakeState.SPEAKING, TurnTakeEvent.CALL_ENDED): TurnTakeState.IDLE,
}


class IllegalTurnTakeTransition(RuntimeError):  # noqa: N818 -- domain-named FSM exception
    """Raised when a state/event pair is not in the transition table."""


@dataclass
class TurnTakeFSM:
    state: TurnTakeState = TurnTakeState.IDLE
    history: list[tuple[TurnTakeState, TurnTakeEvent, TurnTakeState]] = field(
        default_factory=list
    )

    def transition(self, event: TurnTakeEvent) -> TurnTakeState:
        key = (self.state, event)
        nxt = _TRANSITIONS.get(key)
        if nxt is None:
            raise IllegalTurnTakeTransition(
                f"illegal transition: {self.state.value} -[{event.value}]->"
            )
        self.history.append((self.state, event, nxt))
        self.state = nxt
        return nxt

    @property
    def is_speaking(self) -> bool:
        return self.state is TurnTakeState.SPEAKING

    @property
    def can_emit_tts(self) -> bool:
        return self.state in (TurnTakeState.SPEAKING,)

    @staticmethod
    def legal_events(from_state: TurnTakeState) -> tuple[TurnTakeEvent, ...]:
        """Useful for tests + debugging panels."""
        return tuple(ev for (s, ev) in _TRANSITIONS if s == from_state)
