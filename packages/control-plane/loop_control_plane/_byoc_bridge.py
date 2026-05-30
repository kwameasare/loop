"""Sync-from-async bridge for the BYOC channel-credentials resolver.

Channel adapters call a synchronous :class:`ByocCredentialsResolver`
at send time. cp's BYOC store exposes the credentials via an async
``reveal_for_adapter(agent_id, channel_type)`` coroutine. This module
bridges the two so a sync caller (the channel adapter) can pull
plaintext credentials from the async store without dropping into
``asyncio.run`` (which fails when there's already a running loop).

Two callers in mind:

* Sync code with no event loop running → run the coroutine on a
  fresh dedicated loop (``asyncio.run`` works).
* Sync code called from inside an async event loop (e.g. the dp
  runtime's outbound dispatch thread) → schedule the coroutine on a
  worker thread so the calling loop isn't blocked from progressing.

The bridge returns a :class:`ByocCredentialsResolver` that's safe to
hand to any channel BYOC factory (e.g. ``build_byoc_twilio_adapter``).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol
from uuid import UUID

__all__ = [
    "AsyncCredentialsRevealer",
    "make_sync_credentials_resolver",
]


class AsyncCredentialsRevealer(Protocol):
    """The subset of :class:`BYOCSecretService` that the bridge calls.

    Kept narrow so callers don't have to wire the full service when
    a stub will do (and so tests don't need a Postgres engine)."""

    async def reveal_for_adapter(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any]: ...


def _run_coroutine_blocking(coro: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    """Run a coroutine to completion from a sync caller.

    If no event loop is running in this thread, use :func:`asyncio.run`.
    If a loop IS running, schedule the coroutine on a worker thread
    (with its own loop) and block this thread on the result. Blocking
    is acceptable because the calling code already opted into sync
    semantics by calling the resolver — the alternative (raising) would
    force every channel adapter to grow an async surface.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop here — safe to spin one up.
        return asyncio.run(coro)  # type: ignore[arg-type]

    # A loop is running in this thread. Off-load to a worker thread so
    # we don't deadlock on it.
    result_holder: dict[str, Any] = {}
    exc_holder: list[BaseException] = []

    def _runner() -> None:
        try:
            result_holder["value"] = asyncio.run(coro)  # type: ignore[arg-type]
        except BaseException as exc:  # noqa: BLE001
            exc_holder.append(exc)

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join()
    if exc_holder:
        raise exc_holder[0]
    return result_holder["value"]


def make_sync_credentials_resolver(
    byoc_secrets: AsyncCredentialsRevealer,
    *,
    executor: ThreadPoolExecutor | None = None,
) -> Callable[..., dict[str, Any]]:
    """Wrap ``byoc_secrets.reveal_for_adapter`` as a sync callable
    matching :class:`ByocCredentialsResolver`.

    Hand the returned resolver to any channel BYOC factory:

        from loop_channels_sms import build_byoc_twilio_adapter
        from loop_control_plane._byoc_bridge import make_sync_credentials_resolver

        resolver = make_sync_credentials_resolver(cp.byoc_secrets)
        adapter = build_byoc_twilio_adapter(
            agent_id=agent_id,
            resolver=resolver,
            transport_builder=build_twilio_rest_client,
            compliance=compliance,
        )

    The optional ``executor`` arg lets callers share a worker pool
    when many adapters resolve concurrently; if unset we spin a
    one-shot thread per call (cheap, ~µs).
    """

    def _resolve(*, agent_id: UUID, channel_type: str) -> dict[str, Any]:
        coro = byoc_secrets.reveal_for_adapter(
            agent_id=agent_id, channel_type=channel_type
        )
        if executor is not None:
            future = executor.submit(lambda: _run_coroutine_blocking(coro))
            return future.result()
        return _run_coroutine_blocking(coro)

    return _resolve
