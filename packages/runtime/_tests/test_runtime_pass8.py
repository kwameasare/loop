"""Tests for runtime pass8 modules: sse, yaml_serializer, flow_validation."""

from __future__ import annotations

import json

import pytest
from loop_runtime.agent_graph import (
    AgentGraph,
    AgentNode,
    Edge,
    GraphValidationError,
    ParallelOperator,
    TerminalNode,
)
from loop_runtime.flow_validation import (
    FlowIssueKind,
    validate_flow,
)
from loop_runtime.sse import (
    SseEncoder,
    SseEventKind,
    SseFrame,
    SseFrameError,
    encode_done,
    encode_error,
    encode_keepalive,
    encode_turn_event,
)
from loop_runtime.yaml_compiler import compile_flow
from loop_runtime.yaml_serializer import serialize_flow

# ---- SSE (S135) -------------------------------------------------------------


def test_sse_frame_exact_bytes() -> None:
    frame = SseFrame(kind=SseEventKind.TURN_EVENT, event_id=0, data='{"x":1}')
    assert frame.to_bytes() == (
        b"event: turn_event\nid: 0\ndata: {\"x\":1}\n\n"
    )


def test_sse_frame_rejects_newline_in_data() -> None:
    with pytest.raises(SseFrameError):
        SseFrame(kind=SseEventKind.DONE, event_id=0, data="a\nb")


def test_sse_frame_rejects_negative_id() -> None:
    with pytest.raises(SseFrameError):
        SseFrame(kind=SseEventKind.DONE, event_id=-1, data="{}")


def test_sse_encoder_monotonic_ids() -> None:
    enc = SseEncoder()
    a = enc.encode(SseEventKind.TURN_EVENT, {"k": "v"})
    b = enc.encode(SseEventKind.TURN_EVENT, {"k": "v"})
    assert b"id: 0\n" in a
    assert b"id: 1\n" in b
    assert enc.next_id == 2


def test_sse_encoder_helpers() -> None:
    enc = SseEncoder()
    out = b"".join(
        [
            encode_turn_event(enc, {"a": 1}),
            encode_done(enc, turn_id="t-7"),
            encode_error(enc, code="LOOP-RT-001", message="oops"),
            encode_keepalive(enc),
        ]
    )
    blocks = out.split(b"\n\n")
    # 4 frames + trailing empty
    assert len(blocks) == 5
    assert b"event: turn_event\nid: 0" in blocks[0]
    assert b"event: done\nid: 1" in blocks[1]
    assert b'"turn_id":"t-7"' in blocks[1]
    assert b"event: error\nid: 2" in blocks[2]
    assert b"event: keepalive\nid: 3" in blocks[3]


def test_sse_encoder_compact_json() -> None:
    enc = SseEncoder()
    raw = enc.encode(SseEventKind.TURN_EVENT, {"a": 1, "b": [1, 2]})
    # compact form, no spaces
    assert b'data: {"a":1,"b":[1,2]}' in raw


# ---- YAML serializer / compiler round-trip (S465 / S466) --------------------


def _sample_graph() -> AgentGraph:
    return AgentGraph(
        nodes=(
            AgentNode(
                id="planner",
                agent_id="planner-bot",
                input_template="plan: {goal}",
                output_key="plan",
                timeout_ms=15_000,
                agent_version="v3",
            ),
            ParallelOperator(
                id="fanout",
                branch_node_ids=("workerA", "workerB"),
                output_key="results",
                reducer="join_outputs",
            ),
            AgentNode(
                id="workerA",
                agent_id="worker",
                input_template="A {plan}",
                output_key="a_out",
            ),
            AgentNode(
                id="workerB",
                agent_id="worker",
                input_template="B {plan}",
                output_key="b_out",
            ),
            TerminalNode(id="done", output_key="results"),
        ),
        edges=(
            Edge(from_id="planner", to_id="fanout"),
            Edge(from_id="workerA", to_id="done"),
            Edge(from_id="workerB", to_id="done"),
            Edge(from_id="fanout", to_id="done", condition="plan == 'ok'"),
        ),
        entry_id="planner",
        loop_bound=4,
    )


def test_yaml_serialize_roundtrip() -> None:
    g = _sample_graph()
    text = serialize_flow(g)
    g2 = compile_flow(text)
    assert g2 == g


def test_yaml_serialize_omits_defaults() -> None:
    g = AgentGraph(
        nodes=(
            AgentNode(
                id="a",
                agent_id="agent-1",
                input_template="hi",
                output_key="o",
            ),  # defaults: agent_version=latest, timeout_ms=30000
            TerminalNode(id="t", output_key="o"),
        ),
        edges=(Edge(from_id="a", to_id="t"),),
        entry_id="a",
    )
    text = serialize_flow(g)
    assert "agent_version" not in text
    assert "timeout_ms" not in text
    # entry comes first
    assert text.lstrip().startswith("entry:")


def test_yaml_serialize_byte_stable() -> None:
    g = _sample_graph()
    assert serialize_flow(g) == serialize_flow(g)


# ---- flow validation (S470) -------------------------------------------------


def test_flow_validation_clean_graph() -> None:
    issues = validate_flow(_sample_graph())
    assert issues == []


def test_flow_validation_dangling_condition_unknown_key() -> None:
    g = _sample_graph()
    bad = AgentGraph(
        nodes=g.nodes,
        edges=(*g.edges[:-1], Edge(from_id="fanout", to_id="done", condition="ghost == 'x'")),
        entry_id=g.entry_id,
        loop_bound=g.loop_bound,
    )
    issues = validate_flow(bad)
    kinds = [i.kind for i in issues]
    assert FlowIssueKind.DANGLING_CONDITION in kinds


def test_flow_validation_dangling_condition_bad_syntax() -> None:
    g = _sample_graph()
    bad = AgentGraph(
        nodes=g.nodes,
        edges=(*g.edges[:-1], Edge(from_id="fanout", to_id="done", condition="some random text")),
        entry_id=g.entry_id,
        loop_bound=g.loop_bound,
    )
    issues = validate_flow(bad)
    assert any(i.kind is FlowIssueKind.DANGLING_CONDITION for i in issues)


def test_flow_validation_duplicate_output_key() -> None:
    g = AgentGraph(
        nodes=(
            AgentNode(
                id="a",
                agent_id="ag",
                input_template="hi",
                output_key="dup",
            ),
            AgentNode(
                id="b",
                agent_id="ag",
                input_template="hi",
                output_key="dup",
            ),
            TerminalNode(id="t", output_key="dup"),
        ),
        edges=(
            Edge(from_id="a", to_id="b"),
            Edge(from_id="b", to_id="t"),
        ),
        entry_id="a",
    )
    issues = validate_flow(g)
    assert any(i.kind is FlowIssueKind.DUPLICATE_OUTPUT_KEY for i in issues)


def test_flow_validation_terminal_node_excluded_from_duplicate_key() -> None:
    # Terminal's output_key may legitimately match a producer (it
    # *is* the producer of that final key). Validator must not flag.
    g = AgentGraph(
        nodes=(
            AgentNode(
                id="a",
                agent_id="ag",
                input_template="hi",
                output_key="result",
            ),
            TerminalNode(id="t", output_key="result"),
        ),
        edges=(Edge(from_id="a", to_id="t"),),
        entry_id="a",
    )
    assert validate_flow(g) == []


def test_flow_validation_issues_sorted() -> None:
    g = AgentGraph(
        nodes=(
            AgentNode(
                id="a",
                agent_id="ag",
                input_template="hi",
                output_key="dup",
            ),
            AgentNode(
                id="b",
                agent_id="ag",
                input_template="hi",
                output_key="dup",
            ),
            TerminalNode(id="t", output_key="dup"),
        ),
        edges=(
            Edge(from_id="a", to_id="b", condition="ghost == 'x'"),
            Edge(from_id="b", to_id="t"),
        ),
        entry_id="a",
    )
    issues = validate_flow(g)
    # Sorted by (kind, node_id, edge); check we see at least 2 issues
    assert len(issues) >= 2
    keys = [(i.kind.value, i.node_id, i.edge or ("", "")) for i in issues]
    assert keys == sorted(keys)


def test_compile_serialize_compile_idempotent() -> None:
    text = serialize_flow(_sample_graph())
    g1 = compile_flow(text)
    text2 = serialize_flow(g1)
    assert text == text2
    # And the JSON-dumped models match too
    assert json.dumps(g1.model_dump(mode="json"), sort_keys=True) == json.dumps(
        compile_flow(text2).model_dump(mode="json"), sort_keys=True
    )


def test_yaml_compiler_rejects_branches_keyword() -> None:
    # Compiler reads "branches"; ensure serializer's chosen key matches.
    g = _sample_graph()
    text = serialize_flow(g)
    assert "branches:" in text


def test_graph_constructor_rejects_unreachable() -> None:
    from pydantic import ValidationError

    with pytest.raises((GraphValidationError, ValidationError)):
        AgentGraph(
            nodes=(
                AgentNode(
                    id="a",
                    agent_id="ag",
                    input_template="hi",
                    output_key="o",
                ),
                AgentNode(
                    id="orphan",
                    agent_id="ag",
                    input_template="hi",
                    output_key="o2",
                ),
                TerminalNode(id="t", output_key="o"),
            ),
            edges=(Edge(from_id="a", to_id="t"),),
            entry_id="a",
        )
