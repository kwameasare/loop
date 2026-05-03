"""Anthropic streaming provider.

Anthropic ships an event-typed SSE stream; we care about three event kinds::

    event: content_block_delta   data: {"delta":{"text":"hi"}}
    event: message_delta         data: {"usage":{"input_tokens":12,"output_tokens":7}}
    event: message_stop          data: {}

(There are more event types but the others are no-ops for our use case.)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from loop_gateway.cost import cost_for, with_markup
from loop_gateway.providers.base import ProviderBase, StreamTransport
from loop_gateway.providers.httpx_transport import HttpxStreamTransport, ProviderTransportError
from loop_gateway.types import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    Usage,
)


class AnthropicProvider(ProviderBase):
    name = "anthropic"
    supported_prefixes = ("claude-",)

    def __init__(self, transport: StreamTransport | None = None, **transport_kwargs: Any) -> None:
        super().__init__(transport or HttpxStreamTransport("anthropic", **transport_kwargs))

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        usage = Usage(input_tokens=0, output_tokens=0)
        current_event: str | None = None
        try:
            lines = self._transport(request)
            async for line in lines:
                line = line.strip()
                if not line:
                    current_event = None
                    continue
                if line.startswith("event:"):
                    current_event = line[len("event:") :].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                try:
                    obj = json.loads(payload) if payload else {}
                except json.JSONDecodeError as exc:
                    yield GatewayError(code="GW-PARSE", message=str(exc))
                    return
                if current_event == "content_block_delta":
                    text = (obj.get("delta") or {}).get("text")
                    if text:
                        yield GatewayDelta(text=text)
                elif current_event == "message_delta":
                    reported = obj.get("usage") or {}
                    # Anthropic's message_delta carries cumulative usage; replace.
                    usage = Usage(
                        input_tokens=int(reported.get("input_tokens", usage.input_tokens)),
                        output_tokens=int(reported.get("output_tokens", usage.output_tokens)),
                    )
                elif current_event == "message_stop":
                    break
        except ProviderTransportError as exc:
            yield GatewayError(code=exc.code, message=str(exc))
            return
        pass_through = cost_for(request.model, usage.input_tokens, usage.output_tokens)
        yield GatewayDone(usage=usage, cost_usd=with_markup(pass_through))
