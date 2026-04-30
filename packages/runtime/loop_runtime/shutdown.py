"""Graceful shutdown drainer for the dp-runtime (S138).

A FastAPI/asyncio application registers in-flight turns with the drainer.
On shutdown, ``shutdown(deadline_s=30)`` stops accepting new turns and
awaits the registered futures up to the deadline. Anything still running
past the deadline is cancelled and reported in the result summary.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from uuid import UUID

__all__ = [
    "DrainResult",
    "GracefulShutdown",
    "ShutdownError",
]


class ShutdownError(RuntimeError):
    """Raised when register() is called after shutdown has begun."""


@dataclass(frozen=True)
class DrainResult:
    """Summary of a shutdown call. Always returned, never raised."""

    drained: int  # turns that completed cleanly
    cancelled: int  # turns still running at deadline; cancellation requested
    elapsed_s: float


@dataclass
class GracefulShutdown:
    """Tracks in-flight turn tasks and drains them on shutdown.

    Args:
        max_inflight: optional hard cap. ``register`` raises ShutdownError
            if exceeded. ``None`` means uncapped.
    """

    max_inflight: int | None = None
    _tasks: dict[UUID, asyncio.Task[object]] = field(default_factory=dict)
    _shutting_down: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def shutting_down(self) -> bool:
        return self._shutting_down

    @property
    def inflight(self) -> int:
        return len(self._tasks)

    async def register(self, turn_id: UUID, task: asyncio.Task[object]) -> None:
        async with self._lock:
            if self._shutting_down:
                raise ShutdownError("shutting down; new turns rejected")
            if self.max_inflight is not None and len(self._tasks) >= self.max_inflight:
                raise ShutdownError(
                    f"max_inflight={self.max_inflight} reached"
                )
            self._tasks[turn_id] = task
            task.add_done_callback(lambda _t, k=turn_id: self._tasks.pop(k, None))

    async def shutdown(self, *, deadline_s: float = 30.0) -> DrainResult:
        """Stop accepting new turns and drain in-flight up to deadline."""

        async with self._lock:
            self._shutting_down = True
            pending = list(self._tasks.values())

        start = time.monotonic()
        if not pending:
            return DrainResult(drained=0, cancelled=0, elapsed_s=0.0)

        done, not_done = await asyncio.wait(
            pending,
            timeout=max(0.0, deadline_s),
            return_when=asyncio.ALL_COMPLETED,
        )
        cancelled = 0
        for task in not_done:
            task.cancel()
            cancelled += 1
        # Best-effort short await on cancellations to surface immediately.
        if not_done:
            await asyncio.gather(*not_done, return_exceptions=True)
        return DrainResult(
            drained=len(done),
            cancelled=cancelled,
            elapsed_s=time.monotonic() - start,
        )
