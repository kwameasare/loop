"""Token-bucket rate limiter (S117).

Pure-Python in-memory limiter that satisfies the cp-api per-key + per-workspace
budget gate. The clock and storage are pluggable so production can swap the
backend for Redis (using a Lua INCR + EXPIRE script) without changing the
caller surface.

The default backend is a process-local dict guarded by an asyncio Lock so
behaviour matches the contract of the Redis backend (single-thread serialisation
of consume_one for a given key).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

__all__ = [
    "BucketState",
    "InMemoryBucketStore",
    "RateLimitError",
    "RateLimiter",
    "TokenBucketStore",
]


class RateLimitError(RuntimeError):
    """Raised when caller asked for try_consume but a hard error occurred.

    Note: budget-exhausted is *not* an error — ``RateLimiter.try_consume``
    returns False. This exception is for malformed inputs only.
    """


@dataclass(frozen=True)
class BucketState:
    """Snapshot of a single bucket. Returned by inspect()."""

    tokens: float
    last_refill_ms: int


@runtime_checkable
class TokenBucketStore(Protocol):
    """Backend storage for bucket state. The contract is: every load/store
    pair for a given key must be atomic w.r.t other concurrent calls.
    """

    async def load(self, key: str) -> BucketState | None: ...
    async def store(self, key: str, state: BucketState) -> None: ...


@dataclass
class InMemoryBucketStore:
    """asyncio-Lock-guarded process-local store. Production swaps for Redis."""

    _data: dict[str, BucketState] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def load(self, key: str) -> BucketState | None:
        async with self._lock:
            return self._data.get(key)

    async def store(self, key: str, state: BucketState) -> None:
        async with self._lock:
            self._data[key] = state


@dataclass
class RateLimiter:
    """Token-bucket limiter.

    Args:
        capacity: max tokens. Burst allowance.
        refill_per_sec: tokens added per wall-clock second.
        store: pluggable backend. Defaults to in-memory.
        clock_ms: callable returning wall-clock millis (test injection).
    """

    capacity: float
    refill_per_sec: float
    store: TokenBucketStore = field(default_factory=InMemoryBucketStore)
    clock_ms: object = field(default_factory=lambda: lambda: int(time.time() * 1000))

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise RateLimitError("capacity must be > 0")
        if self.refill_per_sec < 0:
            raise RateLimitError("refill_per_sec must be >= 0")

    def _now_ms(self) -> int:
        return int(self.clock_ms())  # type: ignore[operator]

    async def try_consume(self, key: str, *, cost: float = 1.0) -> bool:
        """Attempt to consume ``cost`` tokens from ``key``'s bucket.

        Returns True if granted, False if would exceed capacity.
        """

        if cost <= 0:
            raise RateLimitError("cost must be > 0")
        if cost > self.capacity:
            return False

        now = self._now_ms()
        prior = await self.store.load(key)
        if prior is None:
            tokens = float(self.capacity)
            last = now
        else:
            elapsed_s = max(0, now - prior.last_refill_ms) / 1000.0
            tokens = min(self.capacity, prior.tokens + elapsed_s * self.refill_per_sec)
            last = now

        if tokens + 1e-9 < cost:
            # Persist the refill even on rejection so subsequent calls see
            # the latest accumulated tokens.
            await self.store.store(key, BucketState(tokens=tokens, last_refill_ms=last))
            return False

        await self.store.store(
            key,
            BucketState(tokens=tokens - cost, last_refill_ms=last),
        )
        return True

    async def inspect(self, key: str) -> BucketState | None:
        return await self.store.load(key)
