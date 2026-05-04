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

from loop_voice.connection_pool import (
    ConnectionPoolError,
    PooledWebSocket,
    WarmWebSocketPool,
)
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
from loop_voice.postgres_rooms import PostgresRoomManager
from loop_voice.protocols import (
    InMemoryRealtimeTransport,
    InMemorySpeechToText,
    InMemoryTextToSpeech,
    PrewarmableTextToSpeech,
    RealtimeTransport,
    SpeechToText,
    TextToSpeech,
)
from loop_voice.regional_endpoints import (
    VOICE_PROVIDER_BASE_URLS,
    VOICE_REGIONAL_LATENCY_MS,
    VOICE_REGIONS,
    LatencyMap,
    ProviderEndpointMap,
    ProviderName,
    RegionalEndpointError,
    VoiceRegion,
    VoiceRegionalEndpoint,
    nearest_voice_region,
    provider_base_url,
    resolve_voice_endpoint,
)
from loop_voice.session import (
    AgentResponder,
    StreamingAgentResponder,
    VoiceSession,
    stream_sentence_boundaries,
)
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
    "VOICE_PROVIDER_BASE_URLS",
    "VOICE_REGIONAL_LATENCY_MS",
    "VOICE_REGIONS",
    "AgentResponder",
    "AudioFrame",
    "BudgetBreach",
    "ConnectionPoolError",
    "InMemoryPhoneNumberProvisioner",
    "InMemoryRealtimeTransport",
    "InMemorySpeechToText",
    "InMemoryTextToSpeech",
    "LatencyBudget",
    "LatencyMap",
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
    "PooledWebSocket",
    "PostgresRoomManager",
    "PrewarmableTextToSpeech",
    "ProviderEndpointMap",
    "ProviderName",
    "RealtimeTransport",
    "RegionalEndpointError",
    "SignalKind",
    "SpeechToText",
    "StageBudget",
    "StreamingAgentResponder",
    "TextToSpeech",
    "Transcript",
    "VoiceRegion",
    "VoiceRegionalEndpoint",
    "VoiceSession",
    "VoiceTurn",
    "VoiceTurnState",
    "WarmWebSocketPool",
    "WebRTCError",
    "WebRTCSession",
    "WebRTCSessionRegistry",
    "WebRTCSessionState",
    "WebRTCSignal",
    "echo_answer_for",
    "make_echo_agent",
    "nearest_voice_region",
    "provider_base_url",
    "resolve_voice_endpoint",
    "stream_sentence_boundaries",
    "validate_e164",
]
