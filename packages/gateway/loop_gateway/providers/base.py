"""Provider base + transport seam.

Production code wires a real httpx-backed ``StreamTransport``; tests pass
an in-memory iterator so we get deterministic provider behaviour without
network mocks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from loop_gateway.types import GatewayRequest

# A transport takes a request and yields the upstream's raw text lines
# (one SSE/JSONL line per item). The provider class is responsible for
# parsing those lines into ``GatewayEvent``s.
LineStream = AsyncIterator[str]
StreamTransport = Callable[[GatewayRequest], LineStream]


class ProviderBase:
    """Shared scaffolding: name, supported-model check."""

    name: str
    supported_prefixes: tuple[str, ...] = ()

    def __init__(self, transport: StreamTransport) -> None:
        self._transport = transport

    def supports(self, model: str) -> bool:
        return any(model.startswith(p) for p in self.supported_prefixes)
