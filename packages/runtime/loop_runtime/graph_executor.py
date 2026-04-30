"""Agent-graph executor (S404/S405) — DFS walk with cycle bounds + reducers.

This module is the runtime side of :mod:`loop_runtime.agent_graph`. A
caller hands an :class:`AgentGraph` and a :class:`AgentInvoker`
delegate (the production impl calls the gateway; tests use a fake
that returns canned strings) and gets back the terminal output along
with an execution trace (list of node ids in the order they ran).

Cycle-bounded execution (S405): the graph schema declares
``loop_bound`` as the cap on per-node executions. When a node's count
would exceed this bound the executor raises :class:`LoopBoundExceeded`
with the offending node id, so the caller surfaces a deterministic
error rather than a budget-exhausted timeout.

Edge conditions are evaluated against the shared *state* dict — the
same dict that ``AgentNode.input_template`` substitutes from. This
keeps the model + executor single-source: state in, state out, then
the terminal node reads ``state[output_key]``.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    ParallelOperator,
    ReducerKind,
    TerminalNode,
)

__all__ = [
    "AgentInvoker",
    "ExecutionResult",
    "GraphExecutor",
    "GraphRuntimeError",
    "LoopBoundExceeded",
    "detect_cycles",
]


class GraphRuntimeError(RuntimeError):
    """Generic runtime failure from the graph executor."""


class LoopBoundExceeded(GraphRuntimeError):  # noqa: N818 \u2014 subclass of *Error already.
    """A node would execute more times than ``AgentGraph.loop_bound``."""

    def __init__(self, node_id: str, bound: int) -> None:
        super().__init__(
            f"node {node_id!r} exceeded loop_bound={bound}"
        )
        self.node_id = node_id
        self.bound = bound


@runtime_checkable
class AgentInvoker(Protocol):
    """Single-turn agent call. Implementations adapt to the gateway."""

    async def __call__(
        self,
        *,
        agent_id: str,
        agent_version: str,
        prompt: str,
        timeout_ms: int,
    ) -> str: ...


@dataclass(frozen=True)
class ExecutionResult:
    output: str
    trace: tuple[str, ...]
    state: Mapping[str, str]


# ---------------------------------------------------------------------------
# Cycle detection (S405)
# ---------------------------------------------------------------------------

def detect_cycles(graph: AgentGraph) -> list[list[str]]:
    """Return strongly-connected components > 1 node, plus self-loops.

    The result is empty when the graph is acyclic.
    """
    # Tarjan's SCC.
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    cycles: list[list[str]] = []

    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        adj[e.from_id].append(e.to_id)
        if e.from_id == e.to_id:
            cycles.append([e.from_id])

    def strongconnect(v: str) -> None:
        indices[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj[v]:
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))

    for n in graph.nodes:
        if n.id not in indices:
            strongconnect(n.id)
    return cycles


# ---------------------------------------------------------------------------
# Reducers
# ---------------------------------------------------------------------------

def _reduce(kind: ReducerKind, branch_outputs: list[str]) -> str:
    if kind == "first_non_empty":
        for o in branch_outputs:
            if o:
                return o
        return ""
    if kind == "concat_text":
        return "\n".join(branch_outputs)
    if kind == "join_outputs":
        # Like concat but de-duplicates while preserving order.
        seen: set[str] = set()
        kept: list[str] = []
        for o in branch_outputs:
            if o and o not in seen:
                kept.append(o)
                seen.add(o)
        return "\n".join(kept)
    if kind == "max_score":
        # Heuristic: longest non-empty wins. Real impl reads a score
        # claim from the agent's structured output (deferred slice).
        return max(branch_outputs, key=len, default="")
    raise GraphRuntimeError(f"unknown reducer: {kind!r}")


# ---------------------------------------------------------------------------
# Edge condition DSL
# ---------------------------------------------------------------------------

_CONDITION_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<op>==|!=)\s*"
    r"(?P<rhs>\"[^\"]*\"|'[^']*'|-?\d+)\s*$"
)


def _eval_condition(condition: str, state: Mapping[str, str]) -> bool:
    m = _CONDITION_RE.match(condition)
    if not m:
        raise GraphRuntimeError(f"invalid edge condition: {condition!r}")
    key, op, rhs = m["key"], m["op"], m["rhs"]
    rhs_val = rhs[1:-1] if rhs.startswith(("'", '"')) else rhs
    actual = state.get(key, "")
    return (actual == rhs_val) if op == "==" else (actual != rhs_val)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

@dataclass
class _RunCtx:
    counts: Counter[str] = field(default_factory=Counter)
    trace: list[str] = field(default_factory=list)
    state: dict[str, str] = field(default_factory=dict)


class GraphExecutor:
    """Walks an :class:`AgentGraph` to completion."""

    def __init__(self, invoker: AgentInvoker) -> None:
        self._invoker = invoker

    async def run(
        self,
        graph: AgentGraph,
        *,
        initial_state: Mapping[str, str] | None = None,
    ) -> ExecutionResult:
        ctx = _RunCtx(state=dict(initial_state or {}))
        terminal_id = await self._walk(graph, graph.entry_id, ctx)
        terminal = graph.get_node(terminal_id)
        if not isinstance(terminal, TerminalNode):
            raise GraphRuntimeError(
                f"walk did not end on a terminal node: {terminal_id!r}"
            )
        out = ctx.state.get(terminal.output_key, "")
        return ExecutionResult(
            output=out, trace=tuple(ctx.trace), state=dict(ctx.state)
        )

    async def _walk(
        self, graph: AgentGraph, node_id: str, ctx: _RunCtx
    ) -> str:
        ctx.counts[node_id] += 1
        if ctx.counts[node_id] > graph.loop_bound:
            raise LoopBoundExceeded(node_id, graph.loop_bound)
        ctx.trace.append(node_id)

        node = graph.get_node(node_id)
        if isinstance(node, TerminalNode):
            return node_id
        if isinstance(node, AgentNode):
            await self._invoke_agent(node, ctx)
        elif isinstance(node, ParallelOperator):
            await self._invoke_parallel(graph, node, ctx)

        # Pick the first edge whose condition evaluates true.
        next_id = self._pick_edge(graph.outgoing(node_id), ctx)
        if next_id is None:
            raise GraphRuntimeError(
                f"no outgoing edge satisfied for node {node_id!r}"
            )
        return await self._walk(graph, next_id, ctx)

    async def _invoke_agent(self, node: AgentNode, ctx: _RunCtx) -> None:
        try:
            prompt = node.input_template.format_map(_strict_map(ctx.state))
        except KeyError as exc:
            raise GraphRuntimeError(
                f"agent node {node.id!r} template references missing state key {exc.args[0]!r}"
            ) from exc
        coro: Awaitable[str] = self._invoker(
            agent_id=node.agent_id,
            agent_version=node.agent_version,
            prompt=prompt,
            timeout_ms=node.timeout_ms,
        )
        try:
            output = await asyncio.wait_for(
                _as_awaitable(coro), timeout=node.timeout_ms / 1000
            )
        except TimeoutError as exc:
            raise GraphRuntimeError(
                f"agent node {node.id!r} timed out after {node.timeout_ms}ms"
            ) from exc
        ctx.state[node.output_key] = output

    async def _invoke_parallel(
        self,
        graph: AgentGraph,
        op: ParallelOperator,
        ctx: _RunCtx,
    ) -> None:
        async def _run_branch(branch_id: str) -> str:
            node = graph.get_node(branch_id)
            if not isinstance(node, AgentNode):
                raise GraphRuntimeError(
                    f"parallel branch must be an agent node, got {type(node).__name__}"
                )
            bctx = _RunCtx(
                counts=Counter(ctx.counts),
                state=dict(ctx.state),
            )
            bctx.counts[branch_id] += 1
            if bctx.counts[branch_id] > graph.loop_bound:
                raise LoopBoundExceeded(branch_id, graph.loop_bound)
            await self._invoke_agent(node, bctx)
            return bctx.state.get(node.output_key, "")

        outputs = await asyncio.gather(
            *(_run_branch(b) for b in op.branch_node_ids)
        )
        for branch_id in op.branch_node_ids:
            ctx.counts[branch_id] += 1
            ctx.trace.append(branch_id)
        ctx.state[op.output_key] = _reduce(op.reducer, list(outputs))

    @staticmethod
    def _pick_edge(edges: tuple[Edge, ...] | tuple, ctx: _RunCtx) -> str | None:
        for edge in edges:
            if edge.condition is None or _eval_condition(edge.condition, ctx.state):
                return edge.to_id
        return None


class _strict_map(dict):  # noqa: N801 \u2014 dict subclass; lower-case to match dict-shape conventions.
    """format_map backing that raises KeyError on missing keys (default behaviour)."""


def _as_awaitable(x: Awaitable[str]) -> Awaitable[str]:
    return x
