"""Three-agent supervisor end-to-end acceptance script (S410).

Run with:

    uv run python scripts/multi_e2e.py

The script uses the production graph/executor/cost/trace primitives with a
deterministic in-memory invoker. It asserts the final result, workflow cost
rollup, and cross-agent trace links before printing a compact JSON summary.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from uuid import UUID

from loop_runtime.agent_graph import AgentNode
from loop_runtime.agent_patterns import build_supervisor
from loop_runtime.graph_executor import ExecutionResult, GraphExecutor
from loop_runtime.multi_agent_cost import MultiAgentCostRollup, TurnCostEvent
from loop_runtime.trace_correlation import (
    MultiAgentTrace,
    SpanLinker,
    SpanLinkKind,
    TraceContext,
)


@dataclass(frozen=True)
class MultiE2EResult:
    output: str
    trace: tuple[str, ...]
    total_cost_usd: float
    child_trace_ids: tuple[str, ...]


class DemoInvoker:
    """Deterministic stand-in for agent gateway calls."""

    async def __call__(
        self,
        *,
        agent_id: str,
        agent_version: str,
        prompt: str,
        timeout_ms: int,
    ) -> str:
        del agent_version, timeout_ms
        if agent_id == "agent_supervisor":
            return f"route billing/support for: {prompt}"
        if agent_id == "agent_billing":
            return "billing: refund approved"
        if agent_id == "agent_support":
            return "support: customer notified"
        raise AssertionError(f"unexpected agent_id {agent_id}")


async def run_demo() -> MultiE2EResult:
    supervisor = AgentNode(
        id="supervisor",
        agent_id="agent_supervisor",
        input_template="triage {topic}",
        output_key="task",
    )
    billing = AgentNode(
        id="billing",
        agent_id="agent_billing",
        input_template="{task}",
        output_key="answer",
    )
    support = AgentNode(
        id="support",
        agent_id="agent_support",
        input_template="{task}",
        output_key="answer",
    )
    graph = build_supervisor(
        supervisor=supervisor,
        workers=[billing, support],
        reducer="concat_text",
    )
    result: ExecutionResult = await GraphExecutor(DemoInvoker()).run(
        graph,
        initial_state={"topic": "refund order 1234"},
    )

    parent_turn = UUID("00000000-0000-4000-8000-000000000001")
    billing_turn = UUID("00000000-0000-4000-8000-000000000002")
    support_turn = UUID("00000000-0000-4000-8000-000000000003")
    rollup = MultiAgentCostRollup.aggregate(
        parent=TurnCostEvent(
            turn_id=parent_turn,
            cost_usd_micro=1_500,
            tokens_in=42,
            tokens_out=10,
        ),
        children=[
            TurnCostEvent(
                turn_id=billing_turn,
                parent_turn_id=parent_turn,
                cost_usd_micro=2_000,
                tokens_in=20,
                tokens_out=8,
            ),
            TurnCostEvent(
                turn_id=support_turn,
                parent_turn_id=parent_turn,
                cost_usd_micro=2_500,
                tokens_in=18,
                tokens_out=9,
            ),
        ],
    )

    root = TraceContext(
        trace_id="0" * 31 + "1",
        span_id="0" * 15 + "1",
    )
    billing_ctx = TraceContext(
        trace_id="0" * 31 + "2",
        span_id="0" * 15 + "2",
    )
    support_ctx = TraceContext(
        trace_id="0" * 31 + "3",
        span_id="0" * 15 + "3",
    )
    trace = MultiAgentTrace.build(
        root=root,
        links=[
            SpanLinker.link_child(
                parent=root,
                child=billing_ctx,
                kind=SpanLinkKind.PARENT_TURN,
            ),
            SpanLinker.link_child(
                parent=root,
                child=support_ctx,
                kind=SpanLinkKind.PARENT_TURN,
            ),
        ],
    )

    summary = MultiE2EResult(
        output=result.output,
        trace=result.trace,
        total_cost_usd=rollup.total_cost_usd,
        child_trace_ids=trace.child_trace_ids(),
    )
    assert summary.output == "billing: refund approved\nsupport: customer notified"
    assert summary.trace == (
        "supervisor",
        "__fanout__",
        "billing",
        "support",
        "__end__",
    )
    assert summary.total_cost_usd == 0.006
    assert summary.child_trace_ids == ("0" * 31 + "2", "0" * 31 + "3")
    return summary


def main() -> int:
    summary = asyncio.run(run_demo())
    print(
        json.dumps(
            {
                "output": summary.output,
                "trace": summary.trace,
                "total_cost_usd": summary.total_cost_usd,
                "child_trace_ids": summary.child_trace_ids,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
