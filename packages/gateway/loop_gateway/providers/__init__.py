"""Provider implementations.

Every provider streams. Transports are injectable so unit tests can drive
deterministic event sequences without hitting the network.
"""

from loop_gateway.providers.anthropic import AnthropicProvider
from loop_gateway.providers.base import LineStream, ProviderBase, StreamTransport
from loop_gateway.providers.openai import OpenAIProvider
from loop_gateway.providers.openai_compatible import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTransport,
    OpenAICompatibleProvider,
)

__all__ = [
    "AnthropicProvider",
    "EmbeddingRequest",
    "EmbeddingResult",
    "EmbeddingTransport",
    "LineStream",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "ProviderBase",
    "StreamTransport",
]
