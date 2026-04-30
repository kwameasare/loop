"""Telegram Bot API long-poll driver (S517).

The Bot API exposes ``getUpdates(offset)``: each response includes the
most recent ``update_id``s, and the *next* poll must pass
``offset = max(update_id) + 1`` to acknowledge them. Mis-managing the
offset double-delivers events.

This module implements the offset bookkeeping as a pure async loop that
takes an injected ``GetUpdatesFn`` callable so unit tests can drive
deterministic update streams without hitting Telegram.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

#: Default ``timeout`` query param for getUpdates (long-poll seconds).
DEFAULT_LONG_POLL_TIMEOUT_SECONDS: int = 50
#: Default backoff after an upstream error.
DEFAULT_ERROR_BACKOFF_SECONDS: float = 2.0


GetUpdatesFn = Callable[[int, int], Awaitable[list[dict[str, Any]]]]
"""``async fn(offset, timeout) -> updates``.

Each update is a Bot API ``Update`` object (dict). Callers are
expected to surface network errors as exceptions; the poller converts
them to backoff-with-retry.
"""

UpdateHandler = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PollResult:
    new_offset: int
    delivered: int


@dataclass(slots=True)
class TelegramLongPoller:
    """Stateful long-poll loop with at-least-once delivery semantics."""

    get_updates: GetUpdatesFn
    handler: UpdateHandler
    timeout_seconds: int = DEFAULT_LONG_POLL_TIMEOUT_SECONDS
    error_backoff_seconds: float = DEFAULT_ERROR_BACKOFF_SECONDS
    offset: int = 0
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _consecutive_errors: int = 0

    @property
    def consecutive_errors(self) -> int:
        return self._consecutive_errors

    async def poll_once(self) -> PollResult:
        """Run one ``getUpdates`` cycle. Returns the new offset + count.

        On error returns ``PollResult(self.offset, 0)`` so the loop can
        sleep + retry without losing the current offset.
        """
        try:
            updates = await self.get_updates(self.offset, self.timeout_seconds)
        except Exception:
            self._consecutive_errors += 1
            return PollResult(new_offset=self.offset, delivered=0)
        self._consecutive_errors = 0
        if not updates:
            return PollResult(new_offset=self.offset, delivered=0)
        delivered = 0
        max_id = self.offset - 1
        for update in updates:
            try:
                update_id = int(update["update_id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"telegram update missing update_id: {update!r}") from exc
            await self.handler(update)
            delivered += 1
            if update_id > max_id:
                max_id = update_id
        new_offset = max_id + 1
        self.offset = new_offset
        return PollResult(new_offset=new_offset, delivered=delivered)

    async def run(self) -> None:
        """Drive ``poll_once`` until ``stop()`` is called."""
        while not self._stop.is_set():
            result = await self.poll_once()
            if self._consecutive_errors > 0:
                # Flaky upstream: sleep before retry so we don't burn CPU.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=self.error_backoff_seconds,
                    )
            elif result.delivered == 0:
                # Healthy upstream returned no updates: yield so stop() wins
                # and so a fake (non-blocking) get_updates doesn't busy-loop.
                await asyncio.sleep(0)

    def stop(self) -> None:
        self._stop.set()


__all__ = [
    "DEFAULT_ERROR_BACKOFF_SECONDS",
    "DEFAULT_LONG_POLL_TIMEOUT_SECONDS",
    "GetUpdatesFn",
    "PollResult",
    "TelegramLongPoller",
    "UpdateHandler",
]
