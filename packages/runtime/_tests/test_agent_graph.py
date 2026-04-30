"""Pass6 runtime tests: AgentGraph + executor + patterns."""

from __future__ import annotations

import pytest
from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    TerminalNode,
)
from loop_runtime.agent_patterns import (
    build_parallel,
    build_pipeline,
    build_supervisor,
)
from loop_runtime.graph_executor import (
    GraphExecutor,
    GraphRuntimeError,
    LoopBoundExceeded,
    detect_cycles,
)
from pydantic import ValidationError

# ----- helpers -------------------------------------------------------------


def _agent(id_: str, output_key: str = "answer", tmpl: str = "say {topic}") -> AgentNode:
    return AgentNode(
        id=id_,
        agent_id=f"agent_{id_}",
        agent_version="latest",
        input_template=tmpl,
        output_key=output_key,
    )


class _FakeInvoker:
    """Returns f(prompt) deterministically; records calls."""

    def __init__(self, fn) -> None:
        self.calls: list[str] = []
        self._fn = fn

    async def __call__(self, *, agent_id, agent_version, prompt, timeout_ms):
        self.calls.append(prompt)
        return self._fn(agent_id, prompt)


# ----- model validation ----------------------------------------------------


def test_graph_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        AgentGraph(
            nodes=(_agent("a"), _agent("a"), TerminalNode(id="t", output_key="answer")),
            edges=(Edge(from_id="a", to_id="t"),),
            entry_id="a",
        )


def test_graph_rejects_unreachable_nodes() -> None:
    with pytest.raises(ValidationError, match="unreachable"):
        AgentGraph(
            nodes=(
                _agent("a"),
                _agent("orphan"),
                TerminalNode(id="t", output_key="answer"),
            ),
            edges=(Edge(from_id="a", to_id="t"),),
            entry_id="a",
        )


def test_graph_requires_terminal() -> None:
    with pytest.raises(ValidationError, match="terminal"):
        AgentGraph(
            nodes=(_agent("a"), _agent("b")),
            edges=(Edge(from_id="a", to_id="b"),),
            entry_id="a",
        )


# ----- pipeline (S402) ----------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_runs_steps_in_order() -> None:
    a = _agent("a", output_key="step_a", tmpl="A:{topic}")
    b = _agent("b", output_key="step_b", tmpl="B:{step_a}")
    c = _agent("c", output_key="step_c", tmpl="C:{step_b}")
    graph = build_pipeline(steps=[a, b, c])
    invoker = _FakeInvoker(lambda agent_id, prompt: prompt + "!")
    res = await GraphExecutor(invoker).run(graph, initial_state={"topic": "ai"})
    assert res.output == "C:B:A:ai!!!"
    assert res.trace == ("a", "b", "c", "__end__")
    assert invoker.calls == ["A:ai", "B:A:ai!", "C:B:A:ai!!"]


# ----- supervisor (S401) --------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_fans_out_workers_and_reduces() -> None:
    sup = _agent("sup", output_key="task", tmpl="route:{topic}")
    w1 = _agent("w1", output_key="answer", tmpl="W1<{task}>")
    w2 = _agent("w2", output_key="answer", tmpl="W2<{task}>")
    w3 = _agent("w3", output_key="answer", tmpl="W3<{task}>")
    graph = build_supervisor(
        supervisor=sup, workers=[w1, w2, w3], reducer="concat_text"
    )
    invoker = _FakeInvoker(lambda agent_id, prompt: prompt.upper())
    res = await GraphExecutor(invoker).run(graph, initial_state={"topic": "x"})
    assert res.output == "W1<ROUTE:X>".upper() + "\n" + "W2<ROUTE:X>".upper() + "\n" + "W3<ROUTE:X>".upper()
    # supervisor + parallel + 3 workers + terminal
    assert "sup" in res.trace
    assert "__fanout__" in res.trace
    assert "__end__" in res.trace
    assert all(w in res.trace for w in ("w1", "w2", "w3"))


@pytest.mark.asyncio
async def test_supervisor_max_score_picks_longest() -> None:
    sup = _agent("sup", output_key="task", tmpl="t:{topic}")
    short = _agent("short", output_key="answer", tmpl="hi")
    long = _agent("long", output_key="answer", tmpl="this is a much longer reply")
    graph = build_supervisor(supervisor=sup, workers=[short, long], reducer="max_score")
    invoker = _FakeInvoker(lambda agent_id, prompt: prompt)
    res = await GraphExecutor(invoker).run(graph, initial_state={"topic": "z"})
    assert res.output == "this is a much longer reply"


# ----- parallel (S403) ----------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_first_non_empty_skips_blanks() -> None:
    a = _agent("a", output_key="answer", tmpl="{seed}_a")
    b = _agent("b", output_key="answer", tmpl="{seed}_b")
    graph = build_parallel(branches=[a, b], reducer="first_non_empty")
    invoker = _FakeInvoker(lambda agent_id, prompt: "" if agent_id == "agent_a" else prompt)
    res = await GraphExecutor(invoker).run(graph, initial_state={"seed": "S"})
    assert res.output == "S_b"


# ----- cycle detection (S405) -------------------------------------------


def test_detect_cycles_finds_two_node_loop() -> None:
    a = _agent("a", output_key="x", tmpl="t")
    b = _agent("b", output_key="y", tmpl="t")
    graph = AgentGraph(
        nodes=(a, b, TerminalNode(id="t", output_key="x")),
        edges=(
            Edge(from_id="a", to_id="b"),
            Edge(from_id="b", to_id="a", condition="x == 'go'"),
            Edge(from_id="b", to_id="t"),
        ),
        entry_id="a",
    )
    cycles = detect_cycles(graph)
    assert any(set(c) == {"a", "b"} for c in cycles)


def test_detect_cycles_acyclic_returns_empty() -> None:
    graph = build_pipeline(steps=[_agent("a"), _agent("b")])
    assert detect_cycles(graph) == []


@pytest.mark.asyncio
async def test_loop_bound_exceeded_raises() -> None:
    # Build a tiny self-looping graph: a → t, but a also loops back to a.
    a = _agent("a", output_key="x", tmpl="t")
    graph = AgentGraph(
        nodes=(a, TerminalNode(id="t", output_key="x")),
        edges=(
            Edge(from_id="a", to_id="a", condition="x != 'done'"),
            Edge(from_id="a", to_id="t"),
        ),
        entry_id="a",
        loop_bound=3,
    )
    invoker = _FakeInvoker(lambda agent_id, prompt: "loop")  # never sets x='done'
    with pytest.raises(LoopBoundExceeded) as exc:
        await GraphExecutor(invoker).run(graph)
    assert exc.value.node_id == "a"
    assert exc.value.bound == 3


# ----- edge condition DSL ------------------------------------------------


@pytest.mark.asyncio
async def test_edge_condition_routes_correctly() -> None:
    classifier = _agent("c", output_key="route", tmpl="classify:{q}")
    happy = _agent("happy", output_key="answer", tmpl="happy_path")
    sad = _agent("sad", output_key="answer", tmpl="sad_path")
    graph = AgentGraph(
        nodes=(
            classifier,
            happy,
            sad,
            TerminalNode(id="t", output_key="answer"),
        ),
        edges=(
            Edge(from_id="c", to_id="happy", condition="route == 'good'"),
            Edge(from_id="c", to_id="sad", condition="route != 'good'"),
            Edge(from_id="happy", to_id="t"),
            Edge(from_id="sad", to_id="t"),
        ),
        entry_id="c",
    )

    def fn(agent_id, prompt):
        return "good" if agent_id == "agent_c" else prompt

    invoker = _FakeInvoker(fn)
    res = await GraphExecutor(invoker).run(graph, initial_state={"q": "x"})
    assert res.output == "happy_path"
    assert "sad" not in res.trace


@pytest.mark.asyncio
async def test_template_missing_key_raises() -> None:
    a = _agent("a", output_key="x", tmpl="needs:{nonexistent}")
    graph = build_pipeline(steps=[a])
    with pytest.raises(GraphRuntimeError, match="missing state key"):
        await GraphExecutor(_FakeInvoker(lambda *a: "x")).run(graph)
