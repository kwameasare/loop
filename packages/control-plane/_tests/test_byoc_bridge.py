"""Tests for the sync-from-async BYOC credentials bridge.

Exercises both calling contexts: pure sync (no event loop) and async
caller (loop already running). The latter requires the bridge to
off-load onto a worker thread, otherwise the call would deadlock.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest

from loop_control_plane._byoc_bridge import make_sync_credentials_resolver

AGENT_ID = UUID("00000000-0000-0000-0000-000000000aaa")


class _StubRevealer:
    """Async-only stub that records calls and returns a canned dict."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[tuple[UUID, str]] = []

    async def reveal_for_adapter(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any]:
        self.calls.append((agent_id, channel_type))
        return self._payload


def test_resolver_from_pure_sync_context() -> None:
    """No event loop running → uses asyncio.run directly."""
    revealer = _StubRevealer({"account_sid": "AC1", "auth_token": "tok"})
    resolver = make_sync_credentials_resolver(revealer)
    result = resolver(agent_id=AGENT_ID, channel_type="sms")
    assert result == {"account_sid": "AC1", "auth_token": "tok"}
    assert revealer.calls == [(AGENT_ID, "sms")]


def test_resolver_from_inside_running_event_loop() -> None:
    """Loop already running → bridge off-loads to worker thread.

    The previous design would have raised ``RuntimeError: asyncio.run
    cannot be called from a running event loop``. The bridge runs the
    coroutine on a worker so the calling loop isn't blocked from
    making progress on other tasks.
    """
    revealer = _StubRevealer({"bot_token": "xoxb-…"})

    async def _async_caller() -> dict[str, Any]:
        resolver = make_sync_credentials_resolver(revealer)
        # The resolver is sync but we're calling it from inside a
        # running event loop. The bridge must handle that.
        return resolver(agent_id=AGENT_ID, channel_type="slack")

    result = asyncio.run(_async_caller())
    assert result == {"bot_token": "xoxb-…"}
    assert revealer.calls == [(AGENT_ID, "slack")]


def test_resolver_propagates_revealer_exceptions() -> None:
    """A failure inside the async coroutine surfaces as an exception
    to the sync caller — not silently swallowed."""

    class _AngryRevealer:
        async def reveal_for_adapter(self, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("no creds uploaded")

    resolver = make_sync_credentials_resolver(_AngryRevealer())
    with pytest.raises(RuntimeError, match="no creds uploaded"):
        resolver(agent_id=AGENT_ID, channel_type="sms")
