"""Multi-agent patterns (S401/S402/S403) — graph-builder helpers.

These compose :mod:`loop_runtime.agent_graph` primitives into the three
canonical multi-agent patterns. Each helper returns an ``AgentGraph``
ready for the executor (S404) so customers can pick a pattern without
hand-authoring nodes/edges.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    GraphValidationError,
    ParallelOperator,
    ReducerKind,
    TerminalNode,
)

__all__ = [
    "build_parallel",
    "build_pipeline",
    "build_supervisor",
]


def build_supervisor(
    *,
    supervisor: AgentNode,
    workers: Sequence[AgentNode],
    reducer: ReducerKind = "max_score",
    output_key: str = "answer",
    loop_bound: int = 8,
) -> AgentGraph:
    """One supervisor delegates to N workers, the reducer picks a winner.

    The supervisor's output is fanned out to every worker via a
    :class:`ParallelOperator`, whose result is the graph's terminal
    output. Edge order = worker declaration order.
    """
    if not workers:
        raise GraphValidationError("supervisor requires at least one worker")
    if any(w.id == supervisor.id for w in workers):
        raise GraphValidationError("worker id collides with supervisor id")
    parallel = ParallelOperator(
        id="__fanout__",
        branch_node_ids=tuple(w.id for w in workers),
        reducer=reducer,
        output_key=output_key,
    )
    terminal = TerminalNode(id="__end__", output_key=output_key)
    edges: tuple[Edge, ...] = (
        Edge(from_id=supervisor.id, to_id=parallel.id),
        Edge(from_id=parallel.id, to_id=terminal.id),
    )
    return AgentGraph(
        nodes=(supervisor, parallel, *workers, terminal),
        edges=edges,
        entry_id=supervisor.id,
        loop_bound=loop_bound,
    )


def build_pipeline(
    *,
    steps: Sequence[AgentNode],
    output_key: str | None = None,
    loop_bound: int = 8,
) -> AgentGraph:
    """Linear chain: ``step[0] → step[1] → … → step[n-1] → terminal``.

    The terminal exposes ``steps[-1].output_key`` unless overridden.
    """
    if len(steps) < 1:
        raise GraphValidationError("pipeline requires at least one step")
    final_key = output_key or steps[-1].output_key
    terminal = TerminalNode(id="__end__", output_key=final_key)
    edges: list[Edge] = []
    for a, b in itertools.pairwise(steps):
        edges.append(Edge(from_id=a.id, to_id=b.id))
    edges.append(Edge(from_id=steps[-1].id, to_id=terminal.id))
    return AgentGraph(
        nodes=(*steps, terminal),
        edges=tuple(edges),
        entry_id=steps[0].id,
        loop_bound=loop_bound,
    )


def build_parallel(
    *,
    branches: Sequence[AgentNode],
    reducer: ReducerKind = "concat_text",
    output_key: str = "answer",
    loop_bound: int = 8,
) -> AgentGraph:
    """Fan-out/fan-in: every branch sees the same starting state.

    Implemented as a single :class:`ParallelOperator` entry node fanning
    out into the branches, with a synthetic ``__start__`` agent node
    short-circuited by an empty template. We need an entry that points
    to the operator; using the operator itself as entry is fine since
    operators carry no input templating.
    """
    if len(branches) < 2:
        raise GraphValidationError("parallel requires at least 2 branches")
    operator = ParallelOperator(
        id="__fanout__",
        branch_node_ids=tuple(b.id for b in branches),
        reducer=reducer,
        output_key=output_key,
    )
    terminal = TerminalNode(id="__end__", output_key=output_key)
    edges: tuple[Edge, ...] = (
        Edge(from_id=operator.id, to_id=terminal.id),
    )
    return AgentGraph(
        nodes=(operator, *branches, terminal),
        edges=tuple(edges),
        entry_id=operator.id,
        loop_bound=loop_bound,
    )
