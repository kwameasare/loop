"""Loop voice pipeline.

The pipeline is provider-agnostic. Three structural Protocols capture the
collaborators:

* `RealtimeTransport` -- audio in/out (LiveKit room, WebRTC peer, etc.).
* `SpeechToText` -- streaming or batch ASR (Deepgram, Whisper, etc.).
* `TextToSpeech` -- streaming TTS (ElevenLabs, Cartesia, OpenAI, etc.).

`VoiceSession` orchestrates them: pull audio frames -> ASR partials/finals
-> agent reply (caller-supplied async callable) -> TTS audio -> push back.
The shipped `InMemory*` impls drive the unit tests and the studio dev
runner; the real adapters land in S016b under loop_voice.adapters.
"""

from loop_voice.echo import make_echo_agent
from loop_voice.latency import (
    DEFAULT_BUDGET,
    BudgetBreach,
    LatencyBudget,
    LatencyMeasurement,
    LatencyStage,
    LatencyTracker,
    StageBudget,
)
from loop_voice.models import (
    AudioFrame,
    Transcript,
    VoiceTurn,
    VoiceTurnState,
)
from loop_voice.phone import (
    InMemoryPhoneNumberProvisioner,
    PhoneCapability,
    PhoneNumber,
    PhoneNumberCandidate,
    PhoneNumberProvisioner,
    PhoneNumberSearchQuery,
    PhoneNumberStatus,
    PhoneProvisioningError,
    validate_e164,
)
from loop_voice.protocols import (
    InMemoryRealtimeTransport,
    InMemorySpeechToText,
    InMemoryTextToSpeech,
    RealtimeTransport,
    SpeechToText,
    TextToSpeech,
)
from loop_voice.session import AgentResponder, VoiceSession
from loop_voice.webrtc import (
    SignalKind,
    WebRTCError,
    WebRTCSession,
    WebRTCSessionRegistry,
    WebRTCSessionState,
    WebRTCSignal,
    echo_answer_for,
)

__all__ = [
    "DEFAULT_BUDGET",
    "AgentResponder",
    "AudioFrame",
    "BudgetBreach",
    "InMemoryPhoneNumberProvisioner",
    "InMemoryRealtimeTransport",
    "InMemorySpeechToText",
    "InMemoryTextToSpeech",
    "LatencyBudget",
    "LatencyMeasurement",
    "LatencyStage",
    "LatencyTracker",
    "PhoneCapability",
    "PhoneNumber",
    "PhoneNumberCandidate",
    "PhoneNumberProvisioner",
    "PhoneNumberSearchQuery",
    "PhoneNumberStatus",
    "PhoneProvisioningError",
    "RealtimeTransport",
    "SignalKind",
    "SpeechToText",
    "StageBudget",
    "TextToSpeech",
    "Transcript",
    "VoiceSession",
    "VoiceTurn",
    "VoiceTurnState",
    "WebRTCError",
    "WebRTCSession",
    "WebRTCSessionRegistry",
    "WebRTCSessionState",
    "WebRTCSignal",
    "echo_answer_for",
    "make_echo_agent",
    "validate_e164",
]
