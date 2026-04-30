"""Multi-agent graph types (S400) — composable orchestration primitives.

An ``AgentGraph`` is a directed graph of *nodes* (agent invocations or
fan-out/fan-in operators) connected by *edges* with optional boolean
*conditions*. The graph is the wire-format Loop ships when a customer
declares a multi-agent flow (yaml→graph compiler is S409). The
runtime executor (S404) walks this graph in dependency order; a
separate cycle detector (S405) refuses to run graphs that lack a safe
loop-bound annotation.

Three built-in *patterns* compose into graphs:

* ``Supervisor`` (S401): one supervisor delegates to N workers, picks the
  winner by a reducer.
* ``Pipeline`` (S402): linear chain — output of step ``i`` is the input of
  ``i+1`` via shared state.
* ``Parallel`` (S403): fan-out N branches that share a starting context,
  then reduce results into one.

The model itself contains no I/O — it is a pure pydantic schema. The
executor (``loop_runtime.graph_executor``) provides the runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "AgentGraph",
    "AgentNode",
    "Edge",
    "GraphValidationError",
    "NodeKind",
    "ParallelOperator",
    "ReducerKind",
    "TerminalNode",
]


NodeKind = Literal["agent", "parallel", "terminal"]
ReducerKind = Literal["first_non_empty", "concat_text", "join_outputs", "max_score"]


class GraphValidationError(ValueError):
    """Raised when an :class:`AgentGraph` fails structural validation."""


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AgentNode(_Frozen):
    """Invokes a single agent version with a templated user message.

    ``input_template`` may reference shared-state keys via ``{key}``;
    the executor substitutes them at run time. ``timeout_ms`` lets each
    node carry its own budget so a slow worker cannot stall the graph.
    """

    id: str = Field(min_length=1, max_length=64)
    kind: Literal["agent"] = "agent"
    agent_id: str = Field(min_length=1)
    agent_version: str = Field(default="latest", min_length=1)
    input_template: str = Field(min_length=1, max_length=8_000)
    output_key: str = Field(min_length=1, max_length=64)
    timeout_ms: int = Field(default=30_000, ge=1, le=600_000)


class ParallelOperator(_Frozen):
    """Fan-out / fan-in operator (S403).

    ``branch_node_ids`` are run concurrently with the same shared state;
    each branch's terminal output is collected and ``reducer`` merges
    them under ``output_key``.
    """

    id: str = Field(min_length=1, max_length=64)
    kind: Literal["parallel"] = "parallel"
    branch_node_ids: Annotated[tuple[str, ...], Field(min_length=2, max_length=16)]
    reducer: ReducerKind = "first_non_empty"
    output_key: str = Field(min_length=1, max_length=64)


class TerminalNode(_Frozen):
    """Marks the graph's exit. Carries the final output_key the caller reads."""

    id: str = Field(min_length=1, max_length=64)
    kind: Literal["terminal"] = "terminal"
    output_key: str = Field(min_length=1, max_length=64)


Node = AgentNode | ParallelOperator | TerminalNode


class Edge(_Frozen):
    """Directed edge ``from_id → to_id`` with an optional condition.

    ``condition`` is a tiny expression DSL: ``"<key> == <literal>"`` or
    ``"<key> != <literal>"``; literals are quoted strings or bare
    integers. The executor evaluates the condition against shared
    state. ``None`` means "always traverse this edge".
    """

    from_id: str = Field(min_length=1)
    to_id: str = Field(min_length=1)
    condition: str | None = Field(default=None, max_length=200)


class AgentGraph(_Frozen):
    """Directed graph of agent nodes with declared entry + cycle bound.

    ``loop_bound`` caps how many times any single node may execute in
    one graph run. The executor (S405) refuses to invoke a node whose
    execution count would exceed this bound, raising a structured
    error so the customer sees a deterministic message rather than an
    out-of-budget timeout.
    """

    nodes: Annotated[tuple[Node, ...], Field(min_length=2, max_length=64)]
    edges: Annotated[tuple[Edge, ...], Field(min_length=1)]
    entry_id: str = Field(min_length=1)
    loop_bound: int = Field(default=8, ge=1, le=64)

    @model_validator(mode="after")
    def _validate_structure(self) -> AgentGraph:
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise GraphValidationError("duplicate node id")
        id_set = set(ids)
        if self.entry_id not in id_set:
            raise GraphValidationError(f"entry_id {self.entry_id!r} is not a node")
        terminals = [n.id for n in self.nodes if isinstance(n, TerminalNode)]
        if not terminals:
            raise GraphValidationError("graph must contain at least one terminal node")
        for edge in self.edges:
            if edge.from_id not in id_set:
                raise GraphValidationError(f"edge from_id {edge.from_id!r} not in nodes")
            if edge.to_id not in id_set:
                raise GraphValidationError(f"edge to_id {edge.to_id!r} not in nodes")
        # Reachability: every non-entry node must be reachable from entry.
        # Parallel operators implicitly fan out to their branch_node_ids,
        # so treat those as virtual edges during traversal.
        reachable: set[str] = {self.entry_id}
        frontier = [self.entry_id]
        nodes_by_id = {n.id: n for n in self.nodes}
        while frontier:
            cur = frontier.pop()
            cur_node = nodes_by_id[cur]
            neighbours: list[str] = [
                e.to_id for e in self.edges if e.from_id == cur
            ]
            if isinstance(cur_node, ParallelOperator):
                neighbours.extend(cur_node.branch_node_ids)
            for nb in neighbours:
                if nb not in reachable:
                    reachable.add(nb)
                    frontier.append(nb)
        unreachable = id_set - reachable
        if unreachable:
            raise GraphValidationError(
                f"unreachable nodes: {sorted(unreachable)!r}"
            )
        return self

    def outgoing(self, node_id: str) -> Sequence[Edge]:
        """Return edges leaving ``node_id`` in declaration order."""
        return tuple(e for e in self.edges if e.from_id == node_id)

    def get_node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)
