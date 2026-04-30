"""Tests for runtime pass7 modules: healthz, turn_persistence,
multi_agent_cost, trace_correlation, yaml_compiler."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from loop_runtime.healthz import build_runtime_healthz
from loop_runtime.multi_agent_cost import (
    MultiAgentCostRollup,
    TurnCostEvent,
)
from loop_runtime.trace_correlation import (
    MultiAgentTrace,
    SpanLinker,
    SpanLinkKind,
    TraceContext,
)
from loop_runtime.turn_persistence import (
    InMemoryTurnSink,
    PersistedToolCall,
    PersistedTurn,
    TurnPersistence,
    TurnPersistenceError,
)
from loop_runtime.yaml_compiler import YamlCompileError, compile_flow

# ----- runtime healthz -------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_healthz_default_healthy() -> None:
    info = await build_runtime_healthz(
        version="0.1.0", commit_sha="deadbeef99", build_time="t"
    )
    assert info.status == "healthy"


@pytest.mark.asyncio
async def test_runtime_healthz_otel_down_degraded() -> None:
    async def bad() -> bool:
        return False

    info = await build_runtime_healthz(
        version="0.1.0",
        commit_sha="deadbeef99",
        build_time="t",
        otel_probe=bad,
    )
    assert info.status == "degraded"
    assert info.otel_ok is False


# ----- turn_persistence ------------------------------------------------------


def _turn(turn_id: UUID, conv_id: UUID, ws: UUID) -> PersistedTurn:
    now = datetime.now(UTC)
    return PersistedTurn(
        id=turn_id,
        workspace_id=ws,
        conversation_id=conv_id,
        agent_version_id=uuid4(),
        started_at=now,
        finished_at=now,
        output_text="hi",
        cost_usd=0.001,
        tokens_in=10,
        tokens_out=5,
    )


@pytest.mark.asyncio
async def test_turn_persistence_idempotent_reapply() -> None:
    sink = InMemoryTurnSink()
    svc = TurnPersistence(sink)
    tid, cid, ws = uuid4(), uuid4(), uuid4()
    turn = _turn(tid, cid, ws)
    assert await svc.persist_complete(turn=turn, tool_calls=()) is True
    # second apply with identical row → no-op
    assert await svc.persist_complete(turn=turn, tool_calls=()) is False
    fetched, calls = await svc.lookup(tid)
    assert fetched == turn
    assert calls == ()


@pytest.mark.asyncio
async def test_turn_persistence_divergent_reapply_raises() -> None:
    sink = InMemoryTurnSink()
    svc = TurnPersistence(sink)
    tid, cid, ws = uuid4(), uuid4(), uuid4()
    await svc.persist_complete(turn=_turn(tid, cid, ws), tool_calls=())
    with pytest.raises(TurnPersistenceError):
        # different output_text → divergent
        diverged = _turn(tid, cid, ws).model_copy(update={"output_text": "different"})
        await svc.persist_complete(turn=diverged, tool_calls=())


@pytest.mark.asyncio
async def test_turn_persistence_tool_call_turn_id_mismatch() -> None:
    sink = InMemoryTurnSink()
    svc = TurnPersistence(sink)
    tid, cid, ws = uuid4(), uuid4(), uuid4()
    bad = PersistedToolCall(
        id=uuid4(),
        turn_id=uuid4(),  # mismatched
        tool_name="search",
        arguments_json="{}",
        result_json=None,
        started_at=datetime.now(UTC),
        finished_at=None,
    )
    with pytest.raises(TurnPersistenceError):
        await svc.persist_complete(turn=_turn(tid, cid, ws), tool_calls=[bad])


def test_turn_persistence_count_query_is_parametrised() -> None:
    sql, params = TurnPersistence.select_count_query(uuid4(), uuid4())
    assert ":ws" in sql and ":conv" in sql
    assert "ws" in params and "conv" in params


# ----- multi_agent_cost ------------------------------------------------------


def test_rollup_aggregates_parent_plus_children() -> None:
    parent_id = uuid4()
    parent = TurnCostEvent(
        turn_id=parent_id, cost_usd_micro=1000, tokens_in=10, tokens_out=20
    )
    children = [
        TurnCostEvent(
            turn_id=uuid4(),
            parent_turn_id=parent_id,
            cost_usd_micro=500,
            tokens_in=5,
            tokens_out=8,
        ),
        TurnCostEvent(
            turn_id=uuid4(),
            parent_turn_id=parent_id,
            cost_usd_micro=300,
            tokens_in=3,
            tokens_out=4,
        ),
    ]
    res = MultiAgentCostRollup.aggregate(parent=parent, children=children)
    assert res.parent_cost_usd_micro == 1000
    assert res.children_cost_usd_micro == 800
    assert res.total_cost_usd_micro == 1800
    assert res.total_tokens_in == 18
    assert res.total_tokens_out == 32
    assert len(res.child_breakdown) == 2


def test_rollup_rejects_parent_with_parent_id() -> None:
    pid = uuid4()
    with pytest.raises(ValueError, match="parent"):
        MultiAgentCostRollup.aggregate(
            parent=TurnCostEvent(
                turn_id=pid, parent_turn_id=uuid4(), cost_usd_micro=0, tokens_in=0, tokens_out=0
            ),
            children=[],
        )


def test_rollup_rejects_mismatched_child() -> None:
    parent = TurnCostEvent(turn_id=uuid4(), cost_usd_micro=0, tokens_in=0, tokens_out=0)
    bad = TurnCostEvent(
        turn_id=uuid4(),
        parent_turn_id=uuid4(),  # different parent
        cost_usd_micro=10,
        tokens_in=0,
        tokens_out=0,
    )
    with pytest.raises(ValueError, match="parent_turn_id"):
        MultiAgentCostRollup.aggregate(parent=parent, children=[bad])


# ----- trace_correlation -----------------------------------------------------


def _ctx(t: str = "0" * 32, s: str = "0" * 16) -> TraceContext:
    return TraceContext(trace_id=t, span_id=s)


def test_span_link_emits_otel_attrs() -> None:
    p = _ctx("1" * 32, "1" * 16)
    c = _ctx("2" * 32, "2" * 16)
    link = SpanLinker.link_child(parent=p, child=c, kind=SpanLinkKind.PARENT_TURN)
    attrs = link.to_otel_attrs()
    assert attrs["loop.link.kind"] == "parent_turn"
    assert attrs["loop.link.parent.trace_id"] == "1" * 32
    assert attrs["loop.link.child.span_id"] == "2" * 16


def test_span_link_self_loop_rejected() -> None:
    p = _ctx("a" * 32, "b" * 16)
    with pytest.raises(ValueError):
        SpanLinker.link_child(parent=p, child=p, kind=SpanLinkKind.SUB_TOOL)


def test_invalid_hex_rejected() -> None:
    with pytest.raises(ValueError):
        TraceContext(trace_id="z" * 32, span_id="0" * 16)


def test_multi_agent_trace_aggregates_child_ids() -> None:
    root = _ctx("1" * 32, "1" * 16)
    link1 = SpanLinker.link_child(
        parent=root, child=_ctx("2" * 32, "2" * 16), kind=SpanLinkKind.PARENT_TURN
    )
    link2 = SpanLinker.link_child(
        parent=root, child=_ctx("3" * 32, "3" * 16), kind=SpanLinkKind.SIBLING_TURN
    )
    trace = MultiAgentTrace.build(root=root, links=[link1, link2])
    assert trace.child_trace_ids() == ("2" * 32, "3" * 32)


# ----- yaml_compiler ---------------------------------------------------------


_VALID_FLOW = """\
entry: greet
loop_bound: 4
nodes:
  - id: greet
    kind: agent
    agent_id: greeter
    input_template: "Hello {user_name}"
    output_key: greeting
  - id: end
    kind: terminal
    output_key: greeting
edges:
  - from: greet
    to: end
"""


def test_compile_flow_round_trip() -> None:
    g = compile_flow(_VALID_FLOW)
    assert g.entry_id == "greet"
    assert g.loop_bound == 4
    assert len(g.nodes) == 2
    assert len(g.edges) == 1


def test_compile_flow_invalid_yaml_message() -> None:
    with pytest.raises(YamlCompileError):
        compile_flow(":\n: bad")


def test_compile_flow_missing_entry() -> None:
    with pytest.raises(YamlCompileError):
        compile_flow("nodes: [{id: a, kind: terminal, output_key: x}]\nedges: []\n")


def test_compile_flow_unknown_kind() -> None:
    with pytest.raises(YamlCompileError, match="unknown node kind"):
        compile_flow(
            """
entry: a
nodes:
  - id: a
    kind: nonsense
    output_key: x
  - id: b
    kind: terminal
    output_key: x
edges:
  - from: a
    to: b
"""
        )


def test_compile_flow_top_level_must_be_mapping() -> None:
    with pytest.raises(YamlCompileError):
        compile_flow("- not: a-mapping\n")
