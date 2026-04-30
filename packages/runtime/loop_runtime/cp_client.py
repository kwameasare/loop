"""TTL cache + cp-api lookup client (S132).

The dp-runtime calls the control-plane to resolve workspace + agent +
agent_version on every turn. Real network latency dominates if not cached;
this module gives a clean Protocol + TTL-bounded in-memory cache so the
production wiring just plugs in a real ``Fetcher``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AgentVersionRecord",
    "CpApiClient",
    "CpApiFetcher",
    "CpApiLookupError",
    "TtlCache",
    "WorkspaceRecord",
]

K = TypeVar("K")
V = TypeVar("V")


class CpApiLookupError(LookupError):
    """Raised when the control-plane returns 404 / not-found for a lookup."""


class WorkspaceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    slug: str = Field(min_length=1)
    region: str = Field(min_length=1)


class AgentVersionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    agent_id: UUID
    version: int = Field(ge=1)
    config_json: dict[str, object]
    workspace_id: UUID


@dataclass
class _Entry(Generic[V]):  # noqa: UP046  # legacy Generic[] keeps default_factory ergonomics
    value: V
    expires_at_ms: int


@dataclass
class TtlCache(Generic[K, V]):  # noqa: UP046  # PEP 695 syntax breaks dataclass field defaults
    """Bounded TTL cache with asyncio-safe single-flight semantics."""

    ttl_ms: int = 30_000
    max_entries: int = 1024
    clock_ms: Callable[[], int] = field(
        default_factory=lambda: lambda: int(time.time() * 1000)
    )
    _data: dict[K, _Entry[V]] = field(default_factory=dict)
    _inflight: dict[K, asyncio.Future[V]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        if self.ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        if self.max_entries <= 0:
            raise ValueError("max_entries must be > 0")

    async def get_or_fetch(self, key: K, fetch: Callable[[], object]) -> V:
        """Cache-aside: returns cached value or invokes ``fetch``.

        ``fetch`` may be sync or async. Concurrent calls for the same key
        coalesce into a single fetch (single-flight).
        """

        now = self.clock_ms()
        async with self._lock:
            entry = self._data.get(key)
            if entry is not None and entry.expires_at_ms > now:
                return entry.value
            inflight = self._inflight.get(key)
            if inflight is None:
                future: asyncio.Future[V] = asyncio.get_event_loop().create_future()
                self._inflight[key] = future
                owner = True
            else:
                future = inflight
                owner = False

        if not owner:
            return await future

        try:
            result = fetch()
            if asyncio.iscoroutine(result):
                value = await result
            else:
                value = result  # type: ignore[assignment]
            async with self._lock:
                self._evict_if_full()
                self._data[key] = _Entry(
                    value=value,  # type: ignore[arg-type]
                    expires_at_ms=self.clock_ms() + self.ttl_ms,
                )
            future.set_result(value)  # type: ignore[arg-type]
            return value  # type: ignore[return-value]
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    def _evict_if_full(self) -> None:
        if len(self._data) < self.max_entries:
            return
        # Drop the entry closest to expiry. Cheap O(n) but ``max_entries``
        # is bounded so this stays well below cache hit cost.
        oldest = min(self._data.items(), key=lambda kv: kv[1].expires_at_ms)
        self._data.pop(oldest[0], None)

    def invalidate(self, key: K) -> None:
        self._data.pop(key, None)


class CpApiFetcher(Protocol):
    """Pluggable transport. Production wires httpx; tests pass an in-memory mock."""

    async def fetch_workspace(self, workspace_id: UUID) -> WorkspaceRecord: ...

    async def fetch_agent_version(
        self, *, agent_id: UUID, version: int
    ) -> AgentVersionRecord: ...


@dataclass
class CpApiClient:
    """High-level client used by dp-runtime. Cached per record type."""

    fetcher: CpApiFetcher
    workspace_cache: TtlCache[UUID, WorkspaceRecord] = field(
        default_factory=lambda: TtlCache[UUID, WorkspaceRecord](ttl_ms=30_000)
    )
    agent_cache: TtlCache[tuple[UUID, int], AgentVersionRecord] = field(
        default_factory=lambda: TtlCache[tuple[UUID, int], AgentVersionRecord](
            ttl_ms=30_000
        )
    )

    async def workspace(self, workspace_id: UUID) -> WorkspaceRecord:
        return await self.workspace_cache.get_or_fetch(
            workspace_id,
            lambda: self.fetcher.fetch_workspace(workspace_id),
        )

    async def agent_version(
        self, *, agent_id: UUID, version: int
    ) -> AgentVersionRecord:
        return await self.agent_cache.get_or_fetch(
            (agent_id, version),
            lambda: self.fetcher.fetch_agent_version(
                agent_id=agent_id, version=version
            ),
        )
