"""Provider implementations.

Every provider streams. Transports are injectable so unit tests can drive
deterministic event sequences without hitting the network.
"""

from loop_gateway.providers.anthropic import AnthropicProvider
from loop_gateway.providers.base import LineStream, ProviderBase, StreamTransport
from loop_gateway.providers.httpx_transport import (
    EmptyWorkspaceKeyStore,
    HttpxStreamTransport,
    ProviderTransportError,
    resolver_from_env,
)
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
    "EmptyWorkspaceKeyStore",
    "HttpxStreamTransport",
    "LineStream",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "ProviderBase",
    "ProviderTransportError",
    "StreamTransport",
    "resolver_from_env",
]
