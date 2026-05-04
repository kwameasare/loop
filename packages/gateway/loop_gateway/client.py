"""Streaming gateway client: routes requests to the right provider, applies
the request-id idempotency cache, returns the unified ``GatewayEvent`` stream.

The cache is keyed on ``(workspace_id, request_id)`` only -- cross-workspace
key sharing is a P0 isolation bug, so we never compose a key without a
workspace_id (HANDBOOK + SECURITY.md).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from time import monotonic
from typing import Protocol

from loop_gateway.aliases import resolve
from loop_gateway.types import GatewayEvent, GatewayRequest, Provider


class IdempotencyCache(Protocol):
    async def get(self, workspace_id: str, request_id: str) -> list[GatewayEvent] | None: ...

    async def claim(self, workspace_id: str, request_id: str) -> bool: ...

    async def set(
        self,
        workspace_id: str,
        request_id: str,
        events: list[GatewayEvent],
    ) -> None: ...


class _IdempotencyCache:
    """In-process LRU keyed by (workspace_id, request_id) with a TTL window.

    The default TTL (600s) matches ``LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS``.
    Production wires this to Redis; the in-process map is enough for tests
    and single-pod dev.
    """

    __slots__ = ("_data", "_ttl")

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[tuple[str, str], tuple[float, list[GatewayEvent] | None]] = {}

    async def get(self, workspace_id: str, request_id: str) -> list[GatewayEvent] | None:
        key = (workspace_id, request_id)
        entry = self._data.get(key)
        if entry is None:
            return None
        ts, events = entry
        if monotonic() - ts > self._ttl:
            self._data.pop(key, None)
            return None
        return events

    async def claim(self, workspace_id: str, request_id: str) -> bool:
        key = (workspace_id, request_id)
        entry = self._data.get(key)
        if entry is not None:
            ts, _events = entry
            if monotonic() - ts <= self._ttl:
                return False
            self._data.pop(key, None)
        self._data[key] = (monotonic(), None)
        return True

    async def set(self, workspace_id: str, request_id: str, events: list[GatewayEvent]) -> None:
        self._data[(workspace_id, request_id)] = (monotonic(), events)


class GatewayClient:
    """Pick a provider, stream its events, replay on duplicate request_id."""

    def __init__(
        self,
        providers: list[Provider],
        *,
        ttl_seconds: float = 600.0,
        workspace_overrides: dict[str, dict[str, str]] | None = None,
        idempotency_cache: IdempotencyCache | None = None,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self._providers = providers
        self._ttl_seconds = ttl_seconds
        self._cache = idempotency_cache or _cache_from_env(ttl_seconds)
        self._workspace_overrides = workspace_overrides or {}

    def _pick(self, model: str) -> Provider:
        for p in self._providers:
            if p.supports(model):
                return p
        raise LookupError(f"no provider supports model {model!r}")

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        # 1) Replay if we've seen this (workspace_id, request_id) recently,
        # or wait for another pod's in-flight claim to finish.
        while True:
            replay = await self._cache.get(request.workspace_id, request.request_id)
            if replay is not None:
                for event in replay:
                    yield event
                return
            if await self._cache.claim(request.workspace_id, request.request_id):
                break
            await asyncio.sleep(0.01)

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
        await self._cache.set(request.workspace_id, request.request_id, recorded)


def _cache_from_env(ttl_seconds: float) -> IdempotencyCache:
    redis_url = os.environ.get("LOOP_GATEWAY_REDIS_URL")
    if not redis_url:
        return _IdempotencyCache(ttl_seconds)
    from loop_gateway.idempotency_redis import RedisIdempotencyCache

    return RedisIdempotencyCache.from_url(redis_url, ttl_seconds=ttl_seconds)
