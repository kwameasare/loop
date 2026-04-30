"""Deterministic YAML serializer for :class:`AgentGraph` (S465).

The studio flow editor (S465-S468) round-trips graph → YAML → graph.
We need byte-stable output so:

* git diffs of saved flows are minimal and reviewable
* the cp-api can compute a content-hash of the flow and use it as
  the agent_version digest
* re-saving an unchanged flow produces no spurious git noise

This module is the inverse of :mod:`loop_runtime.yaml_compiler`
(S466 ships ``compile_flow``). The two together satisfy the
"YAML is the durable store" contract.

Why not ``yaml.safe_dump(graph.model_dump())``? Because:

* default block style mixes flow + block, hurting diffability
* pydantic dump emits None fields that the YAML compiler rejects
* discriminator key ordering is non-deterministic across runs

So this module hand-projects each node and pins key order.
"""

from __future__ import annotations

import yaml

from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    ParallelOperator,
    TerminalNode,
)

__all__ = ["serialize_flow"]


def serialize_flow(graph: AgentGraph) -> str:
    """Return the YAML representation of ``graph`` as a string.

    Output is deterministic: every key is placed in a fixed order
    and the document is emitted in block style with sort_keys=False
    so the *intent* order (entry, loop_bound, nodes, edges) wins.
    """
    doc: dict[str, object] = {
        "entry": graph.entry_id,
        "loop_bound": graph.loop_bound,
        "nodes": [_node_dict(n) for n in graph.nodes],
        "edges": [_edge_dict(e) for e in graph.edges],
    }
    return yaml.safe_dump(
        doc,
        sort_keys=False,
        default_flow_style=False,
        width=200,
        allow_unicode=True,
    )


def _node_dict(node: AgentNode | ParallelOperator | TerminalNode) -> dict[str, object]:
    if isinstance(node, AgentNode):
        out: dict[str, object] = {
            "id": node.id,
            "kind": "agent",
            "agent_id": node.agent_id,
        }
        if node.agent_version != "latest":
            out["agent_version"] = node.agent_version
        out["input_template"] = node.input_template
        out["output_key"] = node.output_key
        if node.timeout_ms != 30_000:
            out["timeout_ms"] = node.timeout_ms
        return out
    if isinstance(node, ParallelOperator):
        out = {
            "id": node.id,
            "kind": "parallel",
            "branches": list(node.branch_node_ids),
        }
        if node.reducer != "first_non_empty":
            out["reducer"] = node.reducer
        out["output_key"] = node.output_key
        return out
    if isinstance(node, TerminalNode):
        return {
            "id": node.id,
            "kind": "terminal",
            "output_key": node.output_key,
        }
    raise TypeError(f"unsupported node type: {type(node).__name__}")


def _edge_dict(edge: Edge) -> dict[str, object]:
    out: dict[str, object] = {"from": edge.from_id, "to": edge.to_id}
    if edge.condition is not None:
        out["condition"] = edge.condition
    return out
