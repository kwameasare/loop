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
from loop_gateway.types import GatewayError, GatewayEvent, GatewayRequest, Provider


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
        """Return the first provider supporting `model`. Kept for back-compat;
        new code should call :meth:`_pick_chain` to enumerate the failover order."""
        chain = self._pick_chain(model)
        if not chain:
            raise LookupError(f"no provider supports model {model!r}")
        return chain[0]

    def _pick_chain(self, model: str) -> list[Provider]:
        """Return every registered provider that supports `model`, in
        constructor order. Closes P1 (vega #3): the runtime now has a
        deterministic failover sequence — when the primary provider
        emits a retryable error, the client falls over to the next
        candidate before surfacing the failure to the caller.
        """
        return [p for p in self._providers if p.supports(model)]

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

        # 2) Resolve alias -> concrete model, then enumerate the
        #    failover chain (every registered provider that supports
        #    this model, in constructor order). Most workspaces only
        #    have one supporting provider per model; the chain matters
        #    for byo-keys + multi-vendor pinning where the same model
        #    name is served by multiple vendors.
        concrete_model = resolve(
            request.model,
            self._workspace_overrides.get(request.workspace_id),
        )
        resolved = request.model_copy(update={"model": concrete_model})
        chain = self._pick_chain(concrete_model)
        if not chain:
            raise LookupError(f"no provider supports model {concrete_model!r}")

        # 3) Try each provider in order. We can only fail over BEFORE
        #    yielding any non-error event: once the caller has seen a
        #    delta/token, we're committed to the current provider's
        #    output (otherwise mid-stream provider switching would
        #    duplicate tokens or fork the assistant message).
        recorded: list[GatewayEvent] = []
        last_error: GatewayEvent | None = None
        for attempt_idx, provider in enumerate(chain):
            emitted_payload = False
            attempt_events: list[GatewayEvent] = []
            try:
                async for event in provider.stream(resolved):
                    if isinstance(event, GatewayError):
                        if not emitted_payload and _is_retryable_gateway_error(event):
                            # Retryable + we haven't surfaced anything.
                            # Discard this attempt's events and try the
                            # next provider in the chain.
                            last_error = event
                            break
                        # Non-retryable, OR retryable-but-mid-stream:
                        # surface the error to the caller. The previous
                        # attempt_events have already been yielded
                        # individually; we only need to surface this
                        # error and persist the full transcript.
                        recorded.extend(attempt_events)
                        recorded.append(event)
                        yield event
                        await self._cache.set(
                            request.workspace_id, request.request_id, recorded
                        )
                        return
                    attempt_events.append(event)
                    emitted_payload = True
                    yield event
                else:
                    # Stream completed cleanly (no GatewayError).
                    recorded.extend(attempt_events)
                    await self._cache.set(
                        request.workspace_id, request.request_id, recorded
                    )
                    return
            except (TimeoutError, ConnectionError) as exc:
                # Network-level failures are retryable as long as nothing
                # was yielded.
                if not emitted_payload and attempt_idx < len(chain) - 1:
                    last_error = GatewayError(
                        code="LOOP-GW-402",
                        message=f"{type(exc).__name__}: {exc}",
                    )
                    continue
                # Either we emitted tokens (commit) or we're out of
                # providers to try. attempt_events were already yielded
                # individually -- only the synthesized error needs
                # surfacing now.
                err = GatewayError(
                    code="LOOP-GW-402", message=f"{type(exc).__name__}: {exc}"
                )
                recorded.extend(attempt_events)
                recorded.append(err)
                yield err
                await self._cache.set(
                    request.workspace_id, request.request_id, recorded
                )
                return

        # All providers in the chain returned retryable errors before
        # surfacing any payload. Bubble up the last error so the caller
        # sees a structured failover-exhausted signal.
        if last_error is None:
            last_error = GatewayError(
                code="LOOP-GW-403", message="failover chain exhausted"
            )
        recorded.append(last_error)
        yield last_error
        await self._cache.set(request.workspace_id, request.request_id, recorded)


# Closes vega #3: provider-level retryable error codes — when one of
# these surfaces from a provider before any payload event, the client
# falls over to the next provider in the chain.
_RETRYABLE_GATEWAY_CODES: frozenset[str] = frozenset(
    {
        "LOOP-GW-301",  # provider rate-limit
        "LOOP-GW-401",  # provider 5xx
        "LOOP-GW-402",  # transport / timeout
        "GW-5XX",  # legacy alias used by ProviderFailoverRunner
        "GW-RATE",
        "GW-TIMEOUT",
    }
)


def _is_retryable_gateway_error(event: GatewayError) -> bool:
    return event.code in _RETRYABLE_GATEWAY_CODES


def _cache_from_env(ttl_seconds: float) -> IdempotencyCache:
    redis_url = os.environ.get("LOOP_GATEWAY_REDIS_URL")
    if not redis_url:
        return _IdempotencyCache(ttl_seconds)
    from loop_gateway.idempotency_redis import RedisIdempotencyCache

    return RedisIdempotencyCache.from_url(redis_url, ttl_seconds=ttl_seconds)
