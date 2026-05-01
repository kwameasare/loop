"""Shared adapter for OpenAI-compatible streaming providers.

Mistral, Groq, vLLM, Together, Replicate, Fireworks, and several hosted
Bedrock/Vertex shims all expose enough of the OpenAI SSE shape that one
adapter can parse deltas, usage, embeddings, and local cost accounting.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable

from pydantic import BaseModel, ConfigDict, Field

from loop_gateway.cost import cost_for, with_markup
from loop_gateway.provider_profiles import ProviderProfile
from loop_gateway.providers.base import ProviderBase, StreamTransport
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    Usage,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EmbeddingRequest(_StrictModel):
    request_id: str
    workspace_id: str
    model: str
    inputs: tuple[str, ...] = Field(min_length=1)


class EmbeddingResult(_StrictModel):
    vectors: tuple[tuple[float, ...], ...]
    usage: Usage
    cost_usd: float


EmbeddingTransport = Callable[[EmbeddingRequest], AsyncIterator[str]]


class OpenAICompatibleProvider(ProviderBase):
    """Provider configured by a ``ProviderProfile`` and injectable transports."""

    def __init__(
        self,
        profile: ProviderProfile,
        transport: StreamTransport,
        *,
        embedding_transport: EmbeddingTransport | None = None,
    ) -> None:
        super().__init__(transport)
        self.profile = profile
        self.name = profile.name
        self.supported_prefixes = profile.model_prefixes
        self._embedding_transport = embedding_transport

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        usage = Usage(input_tokens=0, output_tokens=0)
        lines = self._transport(request)
        async for line in lines:
            line = line.strip()
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError as exc:
                yield GatewayError(code="GW-PARSE", message=str(exc))
                return
            if reported_usage := obj.get("usage"):
                usage = _usage_from_payload(reported_usage)
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {}).get("content")
            if delta:
                yield GatewayDelta(text=str(delta))
        try:
            pass_through = cost_for(request.model, usage.input_tokens, usage.output_tokens)
        except KeyError as exc:
            yield GatewayError(code="GW-COST", message=str(exc))
            return
        yield GatewayDone(usage=usage, cost_usd=with_markup(pass_through))

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not self.profile.supports_embeddings:
            raise ValueError(f"provider {self.name!r} does not support embeddings")
        if self._embedding_transport is None:
            raise RuntimeError(f"provider {self.name!r} has no embedding transport")

        usage = Usage(input_tokens=0, output_tokens=0)
        vectors: list[tuple[float, ...]] = []
        async for line in self._embedding_transport(request):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if reported_usage := obj.get("usage"):
                usage = _usage_from_payload(reported_usage)
            for item in obj.get("data", ()):
                values = item.get("embedding", ())
                vectors.append(tuple(float(v) for v in values))
        pass_through = cost_for(request.model, usage.input_tokens, usage.output_tokens)
        return EmbeddingResult(
            vectors=tuple(vectors),
            usage=usage,
            cost_usd=with_markup(pass_through),
        )


def _usage_from_payload(payload: object) -> Usage:
    if not isinstance(payload, dict):
        return Usage(input_tokens=0, output_tokens=0)
    input_tokens = payload.get("prompt_tokens", payload.get("input_tokens", 0))
    output_tokens = payload.get("completion_tokens", payload.get("output_tokens", 0))
    return Usage(input_tokens=int(input_tokens), output_tokens=int(output_tokens))


__all__ = [
    "EmbeddingRequest",
    "EmbeddingResult",
    "EmbeddingTransport",
    "OpenAICompatibleProvider",
]
