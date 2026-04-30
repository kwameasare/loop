"""Strict pydantic v2 voice models."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AudioFrame(_StrictModel):
    """A short slice of PCM audio. Encoding details (sample rate,
    channels, codec) are pinned for the entire session and supplied by
    the transport up front; we keep frames simple bytes here."""

    pcm: bytes
    sequence: int = Field(ge=0)


class Transcript(_StrictModel):
    """ASR result. ``is_final`` separates partials from finals."""

    text: str
    is_final: bool
    confidence: float = Field(ge=0.0, le=1.0)


class VoiceTurnState(StrEnum):
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    DONE = "done"


class VoiceTurn(_StrictModel):
    """One user-utterance -> agent-reply round-trip."""

    id: UUID = Field(default_factory=uuid4)
    user_text: str
    agent_text: str
    state: VoiceTurnState
    duration_ms: int = Field(ge=0)


__all__ = [
    "AudioFrame",
    "Transcript",
    "VoiceTurn",
    "VoiceTurnState",
]
