"""Voice activity detection + barge-in (S366).

A real production stack delegates VAD to a model (Silero, WebRTC
VAD). For unit tests + low-latency hot path we use a simple energy
threshold detector with an *onset hysteresis*: ``onset_frames``
consecutive frames above ``onset_db`` flips the detector to
*speech-active*; ``release_frames`` consecutive frames below
``release_db`` flips it back. This avoids flapping when mic noise
straddles a single threshold.

When the FSM (:mod:`loop_voice.turn_take`) is in ``SPEAKING`` and
the detector flips active, that is a **barge-in** — the runtime
must immediately stop streaming TTS and reset the FSM to
``LISTENING``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loop_voice.turn_take import TurnTakeEvent, TurnTakeFSM, TurnTakeState

__all__ = [
    "BargeInDetector",
    "BargeInEvent",
    "VadConfig",
    "VadDetector",
    "VadState",
]


class VadState(StrEnum):
    SILENT = "silent"
    SPEAKING = "speaking"


class BargeInEvent(StrEnum):
    SPEECH_ONSET = "speech_onset"
    SPEECH_RELEASE = "speech_release"
    BARGE_IN = "barge_in"


@dataclass(frozen=True)
class VadConfig:
    onset_db: float = -35.0
    """Frames above this dBFS count toward speech onset."""
    release_db: float = -45.0
    """Frames below this dBFS count toward release."""
    onset_frames: int = 3
    """Consecutive frames above onset_db to flip to SPEAKING (~60ms @ 50fps)."""
    release_frames: int = 12
    """Consecutive frames below release_db to flip to SILENT (~240ms @ 50fps)."""

    def __post_init__(self) -> None:
        if self.onset_db <= self.release_db:
            raise ValueError("onset_db must be greater than release_db (hysteresis)")
        if self.onset_frames < 1 or self.release_frames < 1:
            raise ValueError("frame counts must be positive")


@dataclass
class VadDetector:
    config: VadConfig = field(default_factory=VadConfig)
    state: VadState = VadState.SILENT
    _above: int = 0
    _below: int = 0

    def feed(self, frame_db: float) -> BargeInEvent | None:
        """Submit one audio frame's energy in dBFS, return a transition event."""
        cfg = self.config
        if self.state is VadState.SILENT:
            if frame_db >= cfg.onset_db:
                self._above += 1
                if self._above >= cfg.onset_frames:
                    self.state = VadState.SPEAKING
                    self._above = 0
                    self._below = 0
                    return BargeInEvent.SPEECH_ONSET
            else:
                self._above = 0
            return None
        # SPEAKING
        if frame_db <= cfg.release_db:
            self._below += 1
            if self._below >= cfg.release_frames:
                self.state = VadState.SILENT
                self._below = 0
                self._above = 0
                return BargeInEvent.SPEECH_RELEASE
        else:
            self._below = 0
        return None


@dataclass
class BargeInDetector:
    """Pairs a :class:`VadDetector` with a :class:`TurnTakeFSM`.

    When the agent is mid-utterance (``SPEAKING``) and the user
    starts talking, we cut TTS and reset to ``LISTENING``. Onsets
    that arrive while the FSM is ``IDLE`` start a normal turn.
    """

    vad: VadDetector
    fsm: TurnTakeFSM
    barge_ins: int = 0

    def feed(self, frame_db: float) -> BargeInEvent | None:
        ev = self.vad.feed(frame_db)
        if ev is BargeInEvent.SPEECH_ONSET:
            if self.fsm.state in (TurnTakeState.SPEAKING, TurnTakeState.THINKING):
                self.fsm.transition(TurnTakeEvent.BARGE_IN)
                self.barge_ins += 1
                return BargeInEvent.BARGE_IN
            if self.fsm.state is TurnTakeState.IDLE:
                self.fsm.transition(TurnTakeEvent.USER_STARTED_TALKING)
            return BargeInEvent.SPEECH_ONSET
        if ev is BargeInEvent.SPEECH_RELEASE and self.fsm.state is TurnTakeState.LISTENING:
            self.fsm.transition(TurnTakeEvent.VAD_SILENCE)
            return BargeInEvent.SPEECH_RELEASE
        return ev
