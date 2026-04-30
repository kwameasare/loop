"""Behavioural tests for the loop-tool-host warm pool."""

from __future__ import annotations

import asyncio

import pytest
from loop_tool_host import (
    InMemorySandboxFactory,
    SandboxBusyError,
    SandboxConfig,
    SandboxStartupError,
    SandboxState,
    WarmPool,
)


def _config() -> SandboxConfig:
    return SandboxConfig(
        workspace_id="ws-1",
        mcp_server="echo",
        image_digest="sha256:" + "a" * 64,
    )


async def _echo(tool: str, arguments: dict[str, object]) -> dict[str, object]:
    return {"tool": tool, "args": arguments}


@pytest.mark.asyncio
async def test_prewarm_creates_min_idle_sandboxes_in_ready_state() -> None:
    factory = InMemorySandboxFactory(_echo)
    pool = WarmPool(config=_config(), factory=factory, min_idle=2, max_size=4)
    await pool.prewarm()
    assert pool.stats().idle == 2
    assert pool.stats().in_flight == 0
    assert all(s.state is SandboxState.READY for s in factory.created)


@pytest.mark.asyncio
async def test_acquire_yields_idle_sandbox_and_releases_back() -> None:
    factory = InMemorySandboxFactory(_echo)
    pool = WarmPool(config=_config(), factory=factory, min_idle=1, max_size=2)
    await pool.prewarm()

    async with pool.acquire() as sandbox:
        assert sandbox.state is SandboxState.READY
        assert pool.stats().in_flight == 1
        assert pool.stats().idle == 0
        result = await sandbox.exec(tool="ping", arguments={"x": 1})
        assert result.ok
        assert result.payload == {"tool": "ping", "args": {"x": 1}}

    assert pool.stats().in_flight == 0
    assert pool.stats().idle == 1


@pytest.mark.asyncio
async def test_acquire_grows_pool_up_to_max_size_then_blocks() -> None:
    factory = InMemorySandboxFactory(_echo)
    pool = WarmPool(
        config=_config(),
        factory=factory,
        min_idle=0,
        max_size=2,
        acquire_timeout_seconds=0.1,
    )

    releases = [asyncio.Event(), asyncio.Event()]
    acks = [asyncio.Event(), asyncio.Event()]

    async def hold_one(release: asyncio.Event, ack: asyncio.Event) -> None:
        async with pool.acquire():
            ack.set()
            await release.wait()

    t1 = asyncio.create_task(hold_one(releases[0], acks[0]))
    t2 = asyncio.create_task(hold_one(releases[1], acks[1]))
    await acks[0].wait()
    await acks[1].wait()

    # third acquire must time out -- pool is full.
    with pytest.raises(SandboxBusyError):
        async with pool.acquire():
            pass  # pragma: no cover

    for ev in releases:
        ev.set()
    await asyncio.gather(t1, t2)
    assert pool.stats().in_flight == 0
    assert pool.stats().idle == 2  # released grew sandboxes returned to idle


@pytest.mark.asyncio
async def test_acquire_waits_for_release_when_under_max_size_pressure() -> None:
    factory = InMemorySandboxFactory(_echo)
    pool = WarmPool(
        config=_config(),
        factory=factory,
        min_idle=0,
        max_size=1,
        acquire_timeout_seconds=2.0,
    )

    release = asyncio.Event()
    holder_acquired = asyncio.Event()

    async def hold() -> None:
        async with pool.acquire():
            holder_acquired.set()
            await release.wait()

    holder = asyncio.create_task(hold())
    await holder_acquired.wait()

    async def waiter_acquires() -> bool:
        async with pool.acquire() as sandbox:
            return sandbox.state is SandboxState.READY

    waiter = asyncio.create_task(waiter_acquires())
    # waiter should still be pending until release fires
    await asyncio.sleep(0.05)
    assert not waiter.done()

    release.set()
    assert await waiter is True
    await holder


@pytest.mark.asyncio
async def test_startup_failure_during_prewarm_propagates_and_does_not_corrupt_pool() -> None:
    factory = InMemorySandboxFactory(_echo, fail_starts=1)
    pool = WarmPool(config=_config(), factory=factory, min_idle=2, max_size=4)
    with pytest.raises(SandboxStartupError):
        await pool.prewarm()
    # The good sandbox(es) that started must still be idle.
    assert pool.stats().idle == 1
    assert pool.stats().in_flight == 0


@pytest.mark.asyncio
async def test_drain_terminates_idle_sandboxes_and_blocks_acquire() -> None:
    factory = InMemorySandboxFactory(_echo)
    pool = WarmPool(config=_config(), factory=factory, min_idle=2, max_size=4)
    await pool.prewarm()
    sandboxes = list(factory.created)

    await pool.drain()
    assert all(s.state is SandboxState.TERMINATED for s in sandboxes)
    assert pool.stats().idle == 0

    with pytest.raises(SandboxBusyError):
        async with pool.acquire():
            pass  # pragma: no cover


@pytest.mark.asyncio
async def test_pool_rejects_invalid_sizing() -> None:
    factory = InMemorySandboxFactory(_echo)
    with pytest.raises(ValueError):
        WarmPool(config=_config(), factory=factory, min_idle=-1, max_size=2)
    with pytest.raises(ValueError):
        WarmPool(config=_config(), factory=factory, min_idle=0, max_size=0)
    with pytest.raises(ValueError):
        WarmPool(config=_config(), factory=factory, min_idle=3, max_size=2)
    with pytest.raises(ValueError):
        WarmPool(
            config=_config(),
            factory=factory,
            min_idle=1,
            max_size=2,
            acquire_timeout_seconds=0,
        )


@pytest.mark.asyncio
async def test_exec_error_in_sandbox_returns_error_result_without_killing_sandbox() -> None:
    async def bad(tool: str, arguments: dict[str, object]) -> object:
        raise RuntimeError("tool blew up")

    factory = InMemorySandboxFactory(bad)
    pool = WarmPool(config=_config(), factory=factory, min_idle=1, max_size=1)
    await pool.prewarm()
    async with pool.acquire() as sandbox:
        result = await sandbox.exec(tool="x", arguments={})
        assert not result.ok
        assert result.error is not None
        assert "tool blew up" in result.error
    # sandbox should be reusable
    assert pool.stats().idle == 1
