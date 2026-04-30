"""WarmPool: prewarmed Firecracker/Kata sandbox pool.

Design goals (ADR-005, ADR-021, ARCHITECTURE.md §5 risk #5):

* Cold-start of a Firecracker microVM with image pull is ~1.5s p99;
  acquiring a *prewarmed* one is ~50ms. The pool keeps `min_idle`
  sandboxes ready so `acquire` is fast in the common case.
* Total concurrency is capped at `max_size` to bound per-tenant
  resource use. Hitting the cap blocks up to `acquire_timeout`,
  then raises `SandboxBusyError` so callers can degrade.
* Acquire/release is single-event-loop safe via an asyncio.Lock +
  Condition. No background tasks except what callers schedule via
  `prewarm()`; the runtime owns the schedule, not the pool.

Out of scope here:

* Pool *eviction* (idle TTL, image-version drain) -- stub method
  `mark_for_drain` flips the pool to drain mode for tests; real k8s
  controller code lives behind `loop_tool_host.kubernetes` (S028).
* Cross-workspace sharing -- never. ADR-026 demands one pool *per*
  ``(workspace_id, mcp_server, image_digest)`` triple, enforced by
  the caller wiring up one `WarmPool` per triple.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from collections.abc import AsyncIterator

from loop_tool_host.errors import SandboxBusyError, SandboxStartupError
from loop_tool_host.models import SandboxConfig, SandboxState, WarmPoolStats
from loop_tool_host.sandbox import Sandbox, SandboxFactory


class WarmPool:
    """Per-(workspace, mcp_server, image_digest) sandbox pool."""

    def __init__(
        self,
        *,
        config: SandboxConfig,
        factory: SandboxFactory,
        min_idle: int = 1,
        max_size: int = 4,
        acquire_timeout_seconds: float = 60.0,
    ) -> None:
        if min_idle < 0:
            raise ValueError("min_idle must be >= 0")
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if min_idle > max_size:
            raise ValueError("min_idle cannot exceed max_size")
        if acquire_timeout_seconds <= 0:
            raise ValueError("acquire_timeout_seconds must be positive")

        self._config = config
        self._factory = factory
        self._min_idle = min_idle
        self._max_size = max_size
        self._acquire_timeout = acquire_timeout_seconds

        self._idle: deque[Sandbox] = deque()
        self._in_flight: set[Sandbox] = set()
        self._lock = asyncio.Lock()
        self._available = asyncio.Condition(self._lock)
        self._draining = False

    # ------------------------------------------------------------------ stats

    def stats(self) -> WarmPoolStats:
        return WarmPoolStats(
            in_flight=len(self._in_flight),
            idle=len(self._idle),
            max_size=self._max_size,
            min_idle=self._min_idle,
        )

    # ---------------------------------------------------------------- prewarm

    async def prewarm(self) -> None:
        """Bring the pool up to ``min_idle``. Safe to call repeatedly;
        each call adds at most ``min_idle - current`` sandboxes.
        Startup failures are *not* retried here -- the caller decides
        whether to retry, log, or surface."""
        if self._draining:
            return
        deficit = self._min_idle - (len(self._idle) + len(self._in_flight))
        if deficit <= 0:
            return
        await asyncio.gather(
            *(self._spawn_idle() for _ in range(deficit)),
            return_exceptions=False,
        )

    async def _spawn_idle(self) -> None:
        sandbox = await self._factory.create(self._config)
        try:
            await sandbox.start()
        except SandboxStartupError:
            with contextlib.suppress(Exception):
                await sandbox.shutdown()
            raise
        async with self._lock:
            if self._draining:
                # raced with drain; tear down immediately.
                await sandbox.shutdown()
                return
            self._idle.append(sandbox)
            self._available.notify()

    # ---------------------------------------------------------------- acquire

    @contextlib.asynccontextmanager
    async def acquire(self) -> AsyncIterator[Sandbox]:
        """Borrow a sandbox for the duration of the ``async with``
        block. Released back to idle on exit (or shut down + replaced
        if it ended in a non-READY state)."""
        sandbox = await self._acquire_one()
        try:
            yield sandbox
        finally:
            await self._release(sandbox)

    async def _acquire_one(self) -> Sandbox:
        if self._draining:
            raise SandboxBusyError("pool is draining")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._acquire_timeout

        async with self._lock:
            while True:
                if self._idle:
                    sandbox = self._idle.popleft()
                    self._in_flight.add(sandbox)
                    return sandbox

                # Room to grow? Spawn under the lock so size accounting
                # cannot race past max_size.
                if len(self._in_flight) < self._max_size:
                    self._lock.release()
                    try:
                        sandbox = await self._factory.create(self._config)
                        await sandbox.start()
                    finally:
                        await self._lock.acquire()
                    self._in_flight.add(sandbox)
                    return sandbox

                # Wait for a release.
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise SandboxBusyError(
                        f"no sandbox available within "
                        f"{self._acquire_timeout:.1f}s "
                        f"(max_size={self._max_size})"
                    )
                try:
                    await asyncio.wait_for(
                        self._available.wait(), timeout=remaining
                    )
                except TimeoutError as exc:
                    raise SandboxBusyError(
                        f"no sandbox available within "
                        f"{self._acquire_timeout:.1f}s "
                        f"(max_size={self._max_size})"
                    ) from exc

    async def _release(self, sandbox: Sandbox) -> None:
        async with self._lock:
            self._in_flight.discard(sandbox)
            healthy = (
                not self._draining
                and sandbox.state is SandboxState.READY
            )
            if healthy:
                self._idle.append(sandbox)
                self._available.notify()
            else:
                # Cannot await shutdown under the lock without risking
                # deadlock with prewarm's _spawn_idle, but it's fine --
                # both only contend on _lock briefly.
                pass

        if not healthy:
            with contextlib.suppress(Exception):
                await sandbox.shutdown()
            # Refill toward min_idle if we've dropped below it.
            if not self._draining:
                stats = self.stats()
                if stats.idle + stats.in_flight < self._min_idle:
                    with contextlib.suppress(SandboxStartupError):
                        await self._spawn_idle()

    # ----------------------------------------------------------------- drain

    async def drain(self) -> None:
        """Shut every sandbox down and refuse further acquires.

        In-flight sandboxes are released by their owning ``acquire``
        contexts; this method only tears down the idle set and flips
        the flag.
        """
        async with self._lock:
            self._draining = True
            idles = list(self._idle)
            self._idle.clear()
            self._available.notify_all()
        for sandbox in idles:
            with contextlib.suppress(Exception):
                await sandbox.shutdown()


__all__ = ["WarmPool"]
