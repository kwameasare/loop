"""Streaming gateway client: routes requests to the right provider, applies
the request-id idempotency cache, returns the unified ``GatewayEvent`` stream.

The cache is keyed on ``(workspace_id, request_id)`` only -- cross-workspace
key sharing is a P0 isolation bug, so we never compose a key without a
workspace_id (HANDBOOK + SECURITY.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from time import monotonic

from loop_gateway.aliases import resolve
from loop_gateway.types import GatewayEvent, GatewayRequest, Provider


class _IdempotencyCache:
    """In-process LRU keyed by (workspace_id, request_id) with a TTL window.

    The default TTL (600s) matches ``LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS``.
    Production wires this to Redis; the in-process map is enough for tests
    and single-pod dev.
    """

    __slots__ = ("_data", "_ttl")

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[tuple[str, str], tuple[float, list[GatewayEvent]]] = {}

    def get(self, workspace_id: str, request_id: str) -> list[GatewayEvent] | None:
        key = (workspace_id, request_id)
        entry = self._data.get(key)
        if entry is None:
            return None
        ts, events = entry
        if monotonic() - ts > self._ttl:
            self._data.pop(key, None)
            return None
        return events

    def set(self, workspace_id: str, request_id: str, events: list[GatewayEvent]) -> None:
        self._data[(workspace_id, request_id)] = (monotonic(), events)


class GatewayClient:
    """Pick a provider, stream its events, replay on duplicate request_id."""

    def __init__(
        self,
        providers: list[Provider],
        *,
        ttl_seconds: float = 600.0,
        workspace_overrides: dict[str, dict[str, str]] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self._providers = providers
        self._cache = _IdempotencyCache(ttl_seconds)
        self._workspace_overrides = workspace_overrides or {}

    def _pick(self, model: str) -> Provider:
        for p in self._providers:
            if p.supports(model):
                return p
        raise LookupError(f"no provider supports model {model!r}")

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        # 1) Replay if we've seen this (workspace_id, request_id) recently.
        replay = self._cache.get(request.workspace_id, request.request_id)
        if replay is not None:
            for event in replay:
                yield event
            return

        # 2) Resolve alias -> concrete model, then pick the provider.
        concrete_model = resolve(
            request.model,
            self._workspace_overrides.get(request.workspace_id),
        )
        resolved = request.model_copy(update={"model": concrete_model})
        provider = self._pick(concrete_model)

        # 3) Stream + record for idempotency replay.
        recorded: list[GatewayEvent] = []
        async for event in provider.stream(resolved):
            recorded.append(event)
            yield event
        self._cache.set(request.workspace_id, request.request_id, recorded)
