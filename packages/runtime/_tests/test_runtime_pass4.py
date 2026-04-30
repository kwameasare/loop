"""Tests for pass4 runtime substance: S138, S139, S132, S133, S134, S136."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from loop_control_plane.rate_limit import RateLimiter
from loop_runtime.auth import (
    ApiKeyClaim,
    ApiKeyVerifier,
    InvalidApiKeyError,
    KeyDirectory,
)
from loop_runtime.cp_client import (
    AgentVersionRecord,
    CpApiClient,
    TtlCache,
    WorkspaceRecord,
)
from loop_runtime.shutdown import GracefulShutdown, ShutdownError
from loop_runtime.tool_registry import ToolRegistryInitError, build_registry
from loop_runtime.turn_rate_limit import TurnRateLimiter
from loop_runtime.workspace_context import (
    WorkspaceContext,
    WorkspaceContextError,
    current_workspace,
    use_workspace,
)


# --------------------------------------------------------------- S138 drain
@pytest.mark.asyncio
async def test_graceful_shutdown_drains_inflight() -> None:
    drainer = GracefulShutdown()
    completed = []

    async def turn(i: int) -> None:
        await asyncio.sleep(0.02)
        completed.append(i)

    for i in range(3):
        t = asyncio.create_task(turn(i))
        await drainer.register(uuid4(), t)
    result = await drainer.shutdown(deadline_s=2.0)
    assert result.drained == 3
    assert result.cancelled == 0
    assert sorted(completed) == [0, 1, 2]


@pytest.mark.asyncio
async def test_graceful_shutdown_cancels_after_deadline() -> None:
    drainer = GracefulShutdown()

    async def slow() -> None:
        await asyncio.sleep(5.0)

    t = asyncio.create_task(slow())
    await drainer.register(uuid4(), t)
    result = await drainer.shutdown(deadline_s=0.05)
    assert result.cancelled == 1
    assert t.cancelled() or t.done()


@pytest.mark.asyncio
async def test_graceful_shutdown_rejects_after_close() -> None:
    drainer = GracefulShutdown()
    await drainer.shutdown(deadline_s=0.0)

    async def noop() -> None:
        pass

    t = asyncio.create_task(noop())
    with pytest.raises(ShutdownError):
        await drainer.register(uuid4(), t)
    await t


# --------------------------------------------------------------- S139 turn rl
@pytest.mark.asyncio
async def test_turn_rate_limiter_enforces_both_tiers() -> None:
    ws_lim = RateLimiter(capacity=5, refill_per_sec=0, clock_ms=lambda: 0)
    agent_lim = RateLimiter(capacity=2, refill_per_sec=0, clock_ms=lambda: 0)
    rl = TurnRateLimiter(workspace_limiter=ws_lim, agent_limiter=agent_lim)
    ws = uuid4()
    agent = uuid4()
    d1 = await rl.admit(workspace_id=ws, agent_id=agent)
    d2 = await rl.admit(workspace_id=ws, agent_id=agent)
    d3 = await rl.admit(workspace_id=ws, agent_id=agent)
    assert d1.admitted and d2.admitted
    assert not d3.admitted
    assert d3.reason == "agent_budget_exceeded"


@pytest.mark.asyncio
async def test_turn_rate_limiter_workspace_block_short_circuits() -> None:
    ws_lim = RateLimiter(capacity=1, refill_per_sec=0, clock_ms=lambda: 0)
    agent_lim = RateLimiter(capacity=10, refill_per_sec=0, clock_ms=lambda: 0)
    rl = TurnRateLimiter(workspace_limiter=ws_lim, agent_limiter=agent_lim)
    ws = uuid4()
    a1, a2 = uuid4(), uuid4()
    assert (await rl.admit(workspace_id=ws, agent_id=a1)).admitted
    decision = await rl.admit(workspace_id=ws, agent_id=a2)
    assert not decision.admitted
    assert decision.reason == "workspace_budget_exceeded"


# --------------------------------------------------------------- S132 cache
@pytest.mark.asyncio
async def test_ttl_cache_hits_within_ttl() -> None:
    clock = [0]
    cache: TtlCache[str, int] = TtlCache(ttl_ms=1000, clock_ms=lambda: clock[0])
    calls = [0]

    async def fetch() -> int:
        calls[0] += 1
        return 42

    assert await cache.get_or_fetch("k", fetch) == 42
    assert await cache.get_or_fetch("k", fetch) == 42
    assert calls[0] == 1
    clock[0] = 2000
    assert await cache.get_or_fetch("k", fetch) == 42
    assert calls[0] == 2


@pytest.mark.asyncio
async def test_ttl_cache_single_flight_coalesces_concurrent_fetches() -> None:
    cache: TtlCache[str, int] = TtlCache(ttl_ms=1000)
    calls = [0]

    async def fetch() -> int:
        calls[0] += 1
        await asyncio.sleep(0.01)
        return 7

    results = await asyncio.gather(
        *(cache.get_or_fetch("k", fetch) for _ in range(10))
    )
    assert results == [7] * 10
    assert calls[0] == 1


@pytest.mark.asyncio
async def test_cp_api_client_caches_per_record_type() -> None:
    ws_id = uuid4()
    agent_id = uuid4()
    workspace = WorkspaceRecord(id=ws_id, slug="acme", region="eu-west-1")
    agentver = AgentVersionRecord(
        agent_id=agent_id, version=1, config_json={}, workspace_id=ws_id
    )

    class StubFetcher:
        def __init__(self) -> None:
            self.ws_calls = 0
            self.agent_calls = 0

        async def fetch_workspace(self, _id: UUID) -> WorkspaceRecord:
            self.ws_calls += 1
            return workspace

        async def fetch_agent_version(
            self, *, agent_id: UUID, version: int
        ) -> AgentVersionRecord:
            self.agent_calls += 1
            return agentver

    fetcher = StubFetcher()
    client = CpApiClient(fetcher=fetcher)
    assert (await client.workspace(ws_id)).slug == "acme"
    assert (await client.workspace(ws_id)).slug == "acme"
    assert fetcher.ws_calls == 1
    assert (await client.agent_version(agent_id=agent_id, version=1)).version == 1
    assert fetcher.agent_calls == 1


# --------------------------------------------------------------- S133 ctx
@pytest.mark.asyncio
async def test_workspace_context_pins_for_block() -> None:
    ws = uuid4()
    ctx = WorkspaceContext(workspace_id=ws, user_sub="u", request_id="r-1")
    async with use_workspace(ctx):
        assert current_workspace().workspace_id == ws


@pytest.mark.asyncio
async def test_workspace_context_outside_block_raises() -> None:
    with pytest.raises(WorkspaceContextError):
        current_workspace()


@pytest.mark.asyncio
async def test_workspace_context_isolates_concurrent_tasks() -> None:
    seen: dict[str, UUID] = {}

    async def worker(name: str, ws_id: UUID) -> None:
        ctx = WorkspaceContext(
            workspace_id=ws_id, user_sub=name, request_id=name
        )
        async with use_workspace(ctx):
            await asyncio.sleep(0.01)
            seen[name] = current_workspace().workspace_id

    a, b = uuid4(), uuid4()
    await asyncio.gather(worker("a", a), worker("b", b))
    assert seen == {"a": a, "b": b}


# --------------------------------------------------------------- S134 keys
@pytest.mark.asyncio
async def test_api_key_verifier_accepts_known_hash_and_caches() -> None:
    ws = uuid4()
    claim = ApiKeyClaim(workspace_id=ws, user_sub="bot", issued_at_ms=0)
    calls = [0]

    class Dir:
        async def lookup_by_hash(self, key_hash_hex: str) -> ApiKeyClaim | None:
            calls[0] += 1
            return claim

    assert isinstance(Dir(), KeyDirectory)
    verifier = ApiKeyVerifier(directory=Dir(), clock_ms=lambda: 0)
    assert (await verifier.verify("sekret")) == claim
    assert (await verifier.verify("sekret")) == claim
    assert calls[0] == 1  # cached


@pytest.mark.asyncio
async def test_api_key_verifier_rejects_empty_and_unknown() -> None:
    class EmptyDir:
        async def lookup_by_hash(self, key_hash_hex: str) -> ApiKeyClaim | None:
            return None

    verifier = ApiKeyVerifier(directory=EmptyDir())
    with pytest.raises(InvalidApiKeyError):
        await verifier.verify("")
    with pytest.raises(InvalidApiKeyError):
        await verifier.verify("anything")


# --------------------------------------------------------------- S136 tools
@pytest.mark.asyncio
async def test_tool_registry_builds_from_config_json() -> None:
    async def search_tool(*, query: str) -> str:
        return f"hit:{query}"

    def search_factory(cfg: Any) -> Any:
        assert cfg.get("top_k") == 5
        return search_tool

    registry = await build_registry(
        {"tools": [{"name": "search", "config": {"top_k": 5}}]},
        factories={"search": search_factory},
    )
    impl = registry.get("search")
    assert impl is not None
    assert await impl(query="foo") == "hit:foo"
    assert registry.names() == ("search",)


@pytest.mark.asyncio
async def test_tool_registry_rejects_unknown_tool() -> None:
    with pytest.raises(ToolRegistryInitError):
        await build_registry(
            {"tools": [{"name": "ghost"}]},
            factories={},
        )


@pytest.mark.asyncio
async def test_tool_registry_rejects_duplicate() -> None:
    async def t(**_: Any) -> str:
        return "x"

    with pytest.raises(ToolRegistryInitError):
        await build_registry(
            {"tools": [{"name": "x"}, {"name": "x"}]},
            factories={"x": lambda _cfg: t},
        )


@pytest.mark.asyncio
async def test_tool_registry_handles_no_tools_key() -> None:
    registry = await build_registry({}, factories={})
    assert registry.names() == ()
