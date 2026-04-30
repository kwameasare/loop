"""Tool-call rate limiting (S722).

Per ADR (rate-limits): tool-host caps tool invocations on two axes
simultaneously \u2014 per ``(workspace_id, tool)`` and per
``(workspace_id, agent_id, tool)``. The first protects shared upstream
quotas; the second prevents one runaway agent from starving siblings.

The bucket is a classic token-bucket with ``capacity`` tokens and a
``refill_per_second`` rate. ``acquire()`` raises ``ToolHostError``
(``LOOP-TH-301``) if the bucket is empty so the caller can return a
typed error frame to the user instead of silently queuing.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from loop_tool_host.errors import ToolHostError


class ToolRateLimitExceeded(ToolHostError):  # noqa: N818
    """Per-tool rate limit was hit."""

    code = "LOOP-TH-301"


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    capacity: float
    refill_per_second: float

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")


@dataclass(slots=True)
class _Bucket:
    tokens: float
    last_refill: float

    def refill(self, now: float, cfg: RateLimitConfig) -> None:
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(cfg.capacity, self.tokens + elapsed * cfg.refill_per_second)
        self.last_refill = now


class TokenBucketLimiter:
    """Thread-unsafe (event-loop scoped) per-key token bucket."""

    def __init__(
        self,
        config: RateLimitConfig,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = config
        self._now = clock
        self._buckets: dict[tuple[str, ...], _Bucket] = {}

    def _bucket(self, key: tuple[str, ...]) -> _Bucket:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=self._cfg.capacity, last_refill=self._now())
            self._buckets[key] = bucket
        return bucket

    def try_acquire(self, key: tuple[str, ...], cost: float = 1.0) -> bool:
        if cost <= 0:
            raise ValueError("cost must be positive")
        bucket = self._bucket(key)
        bucket.refill(self._now(), self._cfg)
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True
        return False

    def acquire(self, key: tuple[str, ...], cost: float = 1.0) -> None:
        if not self.try_acquire(key, cost):
            raise ToolRateLimitExceeded(f"rate limit exceeded for {key!r}")

    def tokens(self, key: tuple[str, ...]) -> float:
        bucket = self._bucket(key)
        bucket.refill(self._now(), self._cfg)
        return bucket.tokens


@dataclass(slots=True)
class ToolRateLimiter:
    """Two-axis rate limiter: per (ws, tool) + per (ws, agent, tool)."""

    per_workspace: TokenBucketLimiter
    per_agent: TokenBucketLimiter

    def acquire(self, *, workspace_id: str, agent_id: str, tool: str) -> None:
        self.per_workspace.acquire((workspace_id, tool))
        # If the second axis fails we have already consumed a workspace
        # token; that is intentional \u2014 it is a fairness signal that
        # the runaway agent is contributing to workspace pressure.
        self.per_agent.acquire((workspace_id, agent_id, tool))


__all__ = [
    "RateLimitConfig",
    "TokenBucketLimiter",
    "ToolRateLimitExceeded",
    "ToolRateLimiter",
]
