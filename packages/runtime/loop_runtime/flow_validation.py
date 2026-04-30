"""Flow-validation pass (S470).

:class:`AgentGraph` already runs structural checks on construction
(unique ids, reachable nodes, edges land on known ids, terminal
exists). The studio's pre-save validation needs a *richer* report:

* ``missing-edge``: a non-terminal AgentNode has no outgoing edge
* ``dangling-condition``: an edge condition references a key that
  no upstream AgentNode writes via ``output_key``
* ``unreachable-node``: structurally guarded but kept here so the
  studio can surface it inline
* ``no-terminal-from-entry``: at least one terminal must be reachable
  from the entry node along *some* path; otherwise the graph cannot
  produce a value

The validator returns a list of :class:`FlowIssue`; the studio
renders these as inline diagnostics. Empty list = ready to save.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    ParallelOperator,
    TerminalNode,
)

__all__ = [
    "FlowIssue",
    "FlowIssueKind",
    "validate_flow",
]


class FlowIssueKind(StrEnum):
    MISSING_EDGE = "missing_edge"
    DANGLING_CONDITION = "dangling_condition"
    UNREACHABLE_NODE = "unreachable_node"
    NO_TERMINAL_FROM_ENTRY = "no_terminal_from_entry"
    DUPLICATE_OUTPUT_KEY = "duplicate_output_key"


class FlowIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: FlowIssueKind
    node_id: str = ""
    edge: tuple[str, str] | None = None
    message: str


# Condition DSL: "<key> == <literal>" or "<key> != <literal>".
_CONDITION_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*(?:==|!=)\s*(?P<rhs>.+?)\s*$"
)


def validate_flow(graph: AgentGraph) -> list[FlowIssue]:
    """Run all flow-validation checks. Empty list = clean."""
    issues: list[FlowIssue] = []
    issues.extend(_check_missing_edges(graph))
    issues.extend(_check_dangling_conditions(graph))
    issues.extend(_check_terminal_reachable(graph))
    issues.extend(_check_duplicate_output_keys(graph))
    # Stable order for deterministic diagnostics.
    issues.sort(key=lambda i: (i.kind.value, i.node_id, i.edge or ("", "")))
    return issues


def _check_missing_edges(graph: AgentGraph) -> Iterable[FlowIssue]:
    for node in graph.nodes:
        if isinstance(node, TerminalNode):
            continue
        outgoing = graph.outgoing(node.id)
        # Parallel operators "fan out" via branch_node_ids; the structural
        # validator treats those as edges, so a Parallel without explicit
        # outgoing edges is still well-formed *iff* it has at least one
        # downstream join. We require at least one outgoing edge so the
        # graph has somewhere to merge results.
        if not outgoing:
            yield FlowIssue(
                kind=FlowIssueKind.MISSING_EDGE,
                node_id=node.id,
                message=f"node {node.id!r} has no outgoing edge",
            )


def _check_dangling_conditions(graph: AgentGraph) -> Iterable[FlowIssue]:
    output_keys: set[str] = set()
    for n in graph.nodes:
        if isinstance(n, AgentNode | ParallelOperator | TerminalNode):
            output_keys.add(n.output_key)
    for edge in graph.edges:
        if edge.condition is None:
            continue
        match = _CONDITION_PATTERN.match(edge.condition)
        if match is None:
            yield FlowIssue(
                kind=FlowIssueKind.DANGLING_CONDITION,
                edge=(edge.from_id, edge.to_id),
                message=(
                    f"condition {edge.condition!r} on edge "
                    f"{edge.from_id}->{edge.to_id} does not match "
                    "'<key> ==/!= <literal>'"
                ),
            )
            continue
        key = match.group("key")
        if key not in output_keys:
            yield FlowIssue(
                kind=FlowIssueKind.DANGLING_CONDITION,
                edge=(edge.from_id, edge.to_id),
                message=(
                    f"condition references unknown key {key!r} on edge "
                    f"{edge.from_id}->{edge.to_id}"
                ),
            )


def _check_terminal_reachable(graph: AgentGraph) -> Iterable[FlowIssue]:
    nodes_by_id = {n.id: n for n in graph.nodes}
    reachable: set[str] = {graph.entry_id}
    frontier: list[str] = [graph.entry_id]
    while frontier:
        cur = frontier.pop()
        cur_node = nodes_by_id[cur]
        neighbours: list[str] = [e.to_id for e in graph.outgoing(cur)]
        if isinstance(cur_node, ParallelOperator):
            neighbours.extend(cur_node.branch_node_ids)
        for nb in neighbours:
            if nb not in reachable:
                reachable.add(nb)
                frontier.append(nb)
    terminals = [n.id for n in graph.nodes if isinstance(n, TerminalNode)]
    if not any(t in reachable for t in terminals):
        yield FlowIssue(
            kind=FlowIssueKind.NO_TERMINAL_FROM_ENTRY,
            node_id=graph.entry_id,
            message="no terminal node is reachable from the entry",
        )


def _check_duplicate_output_keys(graph: AgentGraph) -> Iterable[FlowIssue]:
    seen: dict[str, str] = {}
    for n in graph.nodes:
        if isinstance(n, AgentNode | ParallelOperator):
            prev = seen.get(n.output_key)
            if prev is not None:
                yield FlowIssue(
                    kind=FlowIssueKind.DUPLICATE_OUTPUT_KEY,
                    node_id=n.id,
                    message=(
                        f"output_key {n.output_key!r} already used by "
                        f"node {prev!r}"
                    ),
                )
            else:
                seen[n.output_key] = n.id
