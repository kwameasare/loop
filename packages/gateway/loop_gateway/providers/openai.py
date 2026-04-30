"""OpenAI streaming provider.

Parses the OpenAI Chat Completions SSE format::

    data: {"choices":[{"delta":{"content":"hi"}}]}
    data: {"choices":[{"delta":{"content":" there"}}]}
    data: {"usage":{"prompt_tokens":12,"completion_tokens":7}}
    data: [DONE]

Cost is computed locally from the reported usage so pricing logic stays in
``cost.py`` and we never trust an upstream-reported dollar amount.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from loop_gateway.cost import cost_for, with_markup
from loop_gateway.providers.base import ProviderBase
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    Usage,
)


class OpenAIProvider(ProviderBase):
    name = "openai"
    supported_prefixes = ("gpt-",)

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
                usage = Usage(
                    input_tokens=int(reported_usage.get("prompt_tokens", 0)),
                    output_tokens=int(reported_usage.get("completion_tokens", 0)),
                )
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {}).get("content")
            if delta:
                yield GatewayDelta(text=delta)
        pass_through = cost_for(request.model, usage.input_tokens, usage.output_tokens)
        yield GatewayDone(usage=usage, cost_usd=with_markup(pass_through))
