"""Tests for Parallel + AgentGraph (S042)."""

from __future__ import annotations

import asyncio

import pytest
from loop_runtime import (
    AgentGraph,
    AgentSpec,
    CallableRunner,
    MultiAgentError,
    Parallel,
)


def _runner(prefix: str, *, delay: float = 0.0):
    async def fn(request: str) -> str:
        if delay:
            await asyncio.sleep(delay)
        return f"{prefix}:{request}"

    return CallableRunner(fn)


# -------------------------------------------------------------------- Parallel


@pytest.mark.asyncio
async def test_parallel_fans_out_and_merges() -> None:
    specs = [AgentSpec(name="a"), AgentSpec(name="b"), AgentSpec(name="c")]
    runners = {
        "a": _runner("A"),
        "b": _runner("B"),
        "c": _runner("C"),
    }

    async def merge(pairs):
        return " | ".join(f"{name}={resp}" for name, resp in pairs)

    par = Parallel(specs=specs, runners=runners, merger=merge)
    result = await par.run("hi")

    # Trail order matches spec order, not completion order.
    assert [s.agent for s in result.trail.steps] == ["a", "b", "c"]
    assert result.output == "a=A:hi | b=B:hi | c=C:hi"


@pytest.mark.asyncio
async def test_parallel_actually_concurrent() -> None:
    # If runners ran sequentially, total time would be ~0.3s; concurrent
    # should be ~0.1s. We assert << sum and >= max for fairness.
    specs = [AgentSpec(name="a"), AgentSpec(name="b"), AgentSpec(name="c")]
    runners = {
        "a": _runner("A", delay=0.05),
        "b": _runner("B", delay=0.05),
        "c": _runner("C", delay=0.05),
    }

    async def merge(pairs):
        return ",".join(name for name, _ in pairs)

    par = Parallel(specs=specs, runners=runners, merger=merge)
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    result = await par.run("x")
    elapsed = loop.time() - t0
    assert result.output == "a,b,c"
    # Concurrent: well below the 0.15s sequential lower bound.
    assert elapsed < 0.12


@pytest.mark.asyncio
async def test_parallel_empty_specs_raises() -> None:
    async def merge(_pairs):
        return ""

    with pytest.raises(MultiAgentError):
        Parallel(specs=[], runners={}, merger=merge)


@pytest.mark.asyncio
async def test_parallel_missing_runner_raises() -> None:
    async def merge(_pairs):
        return ""

    with pytest.raises(MultiAgentError):
        Parallel(
            specs=[AgentSpec(name="a"), AgentSpec(name="b")],
            runners={"a": _runner("A")},
            merger=merge,
        )


@pytest.mark.asyncio
async def test_parallel_duplicate_names_raises() -> None:
    async def merge(_pairs):
        return ""

    with pytest.raises(MultiAgentError):
        Parallel(
            specs=[AgentSpec(name="a"), AgentSpec(name="a")],
            runners={"a": _runner("A")},
            merger=merge,
        )


# ------------------------------------------------------------------ AgentGraph


@pytest.mark.asyncio
async def test_graph_walks_until_selector_returns_none() -> None:
    specs = [AgentSpec(name="planner"), AgentSpec(name="worker")]
    runners = {
        "planner": _runner("PLAN"),
        "worker": _runner("WORK"),
    }
    sequence = iter(["worker", None])

    async def selector(_last_agent, _last_response, _trail):
        return next(sequence)

    graph = AgentGraph(
        specs=specs,
        runners=runners,
        selector=selector,
        start="planner",
    )
    result = await graph.run("go")
    assert [s.agent for s in result.trail.steps] == ["planner", "worker"]
    assert result.output == "WORK:PLAN:go"


@pytest.mark.asyncio
async def test_graph_supports_cycles() -> None:
    specs = [AgentSpec(name="a"), AgentSpec(name="b")]
    runners = {"a": _runner("A"), "b": _runner("B")}
    sequence = iter(["b", "a", "b", None])

    async def selector(_last_agent, _last_response, _trail):
        return next(sequence)

    graph = AgentGraph(
        specs=specs, runners=runners, selector=selector, start="a"
    )
    result = await graph.run("seed")
    assert [s.agent for s in result.trail.steps] == ["a", "b", "a", "b"]


@pytest.mark.asyncio
async def test_graph_max_steps_bounds_runaway_cycle() -> None:
    specs = [AgentSpec(name="a")]
    runners = {"a": _runner("A")}

    async def selector(_la, _lr, _t):
        return "a"  # never terminates

    graph = AgentGraph(
        specs=specs,
        runners=runners,
        selector=selector,
        start="a",
        max_steps=3,
    )
    with pytest.raises(MultiAgentError):
        await graph.run("seed")


@pytest.mark.asyncio
async def test_graph_unknown_start_raises() -> None:
    async def selector(_la, _lr, _t):
        return None

    with pytest.raises(MultiAgentError):
        AgentGraph(
            specs=[AgentSpec(name="a")],
            runners={"a": _runner("A")},
            selector=selector,
            start="missing",
        )


@pytest.mark.asyncio
async def test_graph_selector_returning_unknown_raises() -> None:
    async def selector(_la, _lr, _t):
        return "missing"

    graph = AgentGraph(
        specs=[AgentSpec(name="a")],
        runners={"a": _runner("A")},
        selector=selector,
        start="a",
    )
    with pytest.raises(MultiAgentError):
        await graph.run("seed")


@pytest.mark.asyncio
async def test_graph_max_steps_must_be_positive() -> None:
    async def selector(_la, _lr, _t):
        return None

    with pytest.raises(MultiAgentError):
        AgentGraph(
            specs=[AgentSpec(name="a")],
            runners={"a": _runner("A")},
            selector=selector,
            start="a",
            max_steps=0,
        )
