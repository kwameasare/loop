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

from loop_voice.models import (
    AudioFrame,
    Transcript,
    VoiceTurn,
    VoiceTurnState,
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

__all__ = [
    "AgentResponder",
    "AudioFrame",
    "InMemoryRealtimeTransport",
    "InMemorySpeechToText",
    "InMemoryTextToSpeech",
    "RealtimeTransport",
    "SpeechToText",
    "TextToSpeech",
    "Transcript",
    "VoiceSession",
    "VoiceTurn",
    "VoiceTurnState",
]
