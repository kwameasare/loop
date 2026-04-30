"""YAML → :class:`AgentGraph` compiler (S409).

The customer-facing flow definition is a YAML document like::

    entry: greet
    loop_bound: 4
    nodes:
      - id: greet
        kind: agent
        agent_id: greeter
        input_template: "Hello {user_name}!"
        output_key: greeting
      - id: end
        kind: terminal
        output_key: greeting
    edges:
      - from: greet
        to: end

This module compiles that into an :class:`AgentGraph` with the same
validations the runtime applies. Errors carry a structured
``YamlCompileError`` so the cp-api can surface a precise message
(line+key) to the customer, instead of the raw pydantic stack.
"""

from __future__ import annotations

from typing import Any

import yaml

from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    GraphValidationError,
    ParallelOperator,
    TerminalNode,
)

__all__ = ["YamlCompileError", "compile_flow"]


class YamlCompileError(ValueError):
    """Customer-facing compile error with a key path for context."""

    def __init__(self, message: str, *, key_path: str | None = None) -> None:
        self.key_path = key_path
        suffix = f" at {key_path}" if key_path else ""
        super().__init__(f"{message}{suffix}")


def _node_from_dict(raw: Any, *, idx: int) -> AgentNode | ParallelOperator | TerminalNode:
    if not isinstance(raw, dict):
        raise YamlCompileError("node must be a mapping", key_path=f"nodes[{idx}]")
    kind = raw.get("kind")
    if kind == "agent":
        try:
            return AgentNode(
                id=str(raw["id"]),
                agent_id=str(raw["agent_id"]),
                agent_version=str(raw.get("agent_version", "latest")),
                input_template=str(raw["input_template"]),
                output_key=str(raw["output_key"]),
                timeout_ms=int(raw.get("timeout_ms", 30_000)),
            )
        except KeyError as e:
            raise YamlCompileError(
                f"missing required field {e.args[0]!r}", key_path=f"nodes[{idx}]"
            ) from e
    if kind == "parallel":
        try:
            return ParallelOperator(
                id=str(raw["id"]),
                branch_node_ids=tuple(str(b) for b in raw["branches"]),
                reducer=raw.get("reducer", "first_non_empty"),
                output_key=str(raw["output_key"]),
            )
        except KeyError as e:
            raise YamlCompileError(
                f"missing required field {e.args[0]!r}", key_path=f"nodes[{idx}]"
            ) from e
    if kind == "terminal":
        try:
            return TerminalNode(id=str(raw["id"]), output_key=str(raw["output_key"]))
        except KeyError as e:
            raise YamlCompileError(
                f"missing required field {e.args[0]!r}", key_path=f"nodes[{idx}]"
            ) from e
    raise YamlCompileError(
        f"unknown node kind {kind!r}", key_path=f"nodes[{idx}].kind"
    )


def _edge_from_dict(raw: Any, *, idx: int) -> Edge:
    if not isinstance(raw, dict):
        raise YamlCompileError("edge must be a mapping", key_path=f"edges[{idx}]")
    try:
        return Edge(
            from_id=str(raw["from"]),
            to_id=str(raw["to"]),
            condition=raw.get("condition"),
        )
    except KeyError as e:
        raise YamlCompileError(
            f"missing required field {e.args[0]!r}", key_path=f"edges[{idx}]"
        ) from e


def compile_flow(text: str) -> AgentGraph:
    """Parse a flow YAML document and return an :class:`AgentGraph`."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise YamlCompileError(f"invalid YAML: {e}") from e
    if not isinstance(doc, dict):
        raise YamlCompileError("top-level document must be a mapping")
    raw_nodes = doc.get("nodes")
    raw_edges = doc.get("edges")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise YamlCompileError("`nodes` must be a non-empty list", key_path="nodes")
    if not isinstance(raw_edges, list) or not raw_edges:
        raise YamlCompileError("`edges` must be a non-empty list", key_path="edges")
    nodes = tuple(_node_from_dict(n, idx=i) for i, n in enumerate(raw_nodes))
    edges = tuple(_edge_from_dict(e, idx=i) for i, e in enumerate(raw_edges))
    entry_id = doc.get("entry")
    if not isinstance(entry_id, str) or not entry_id:
        raise YamlCompileError("`entry` is required and must be a string", key_path="entry")
    loop_bound = int(doc.get("loop_bound", 8))
    try:
        return AgentGraph(
            nodes=nodes, edges=edges, entry_id=entry_id, loop_bound=loop_bound
        )
    except GraphValidationError as e:
        raise YamlCompileError(str(e)) from e
