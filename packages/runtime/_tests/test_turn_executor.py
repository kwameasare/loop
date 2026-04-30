"""TurnExecutor tests covering single-pass + multi-iteration tool dispatch.

Single-pass cases (carried from S008) keep regression coverage for
streaming, request shape, idempotency, budget/error degrade, and the
otel span. Multi-iteration cases exercise S012: parallel tool dispatch
via asyncio.gather, partial tool failures, and the
``max_iterations`` / unannounced-tools degrade paths.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from loop.types import AgentEvent, ChannelType, ContentPart
from loop_gateway import (
    GatewayDelta,
    GatewayDone,
    GatewayError,
    GatewayEvent,
    GatewayRequest,
    ToolCall,
    ToolSpec,
    Usage,
)
from loop_runtime import AgentConfig, TurnBudget, TurnExecutor

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeGateway:
    """Yields a scripted sequence; records every request seen for assertions."""

    def __init__(self, events: list[GatewayEvent]) -> None:
        self.events = events
        self.last_request: GatewayRequest | None = None
        self.requests_seen: list[GatewayRequest] = []

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        self.last_request = request
        self.requests_seen.append(request)
        for ev in self.events:
            yield ev


class _ScriptedGateway:
    """Yields a different script per call -- one per reasoning iteration."""

    def __init__(self, scripts: list[list[GatewayEvent]]) -> None:
        self._scripts = list(scripts)
        self.requests_seen: list[GatewayRequest] = []

    async def stream(self, request: GatewayRequest) -> AsyncIterator[GatewayEvent]:
        self.requests_seen.append(request)
        if not self._scripts:
            raise AssertionError("gateway called more times than scripted")
        events = self._scripts.pop(0)
        for ev in events:
            yield ev


class _FakeRegistry:
    """A ToolRegistryLike implementation backed by an in-memory dict."""

    def __init__(
        self,
        impls: dict[str, Any],
        specs: list[ToolSpec] | None = None,
    ) -> None:
        self._impls = impls
        self._specs = specs or [
            ToolSpec(
                name=name,
                description="",
                input_schema={"type": "object", "properties": {}},
            )
            for name in impls
        ]
        self.calls_made: list[tuple[str, dict[str, Any]]] = []

    def describe_specs(self) -> list[ToolSpec]:
        return list(self._specs)

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls_made.append((name, arguments))
        impl = self._impls[name]
        return await impl(arguments) if inspect.iscoroutinefunction(impl) else impl(arguments)


def _event(text: str = "hello") -> AgentEvent:
    return AgentEvent(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        user_id="u-1",
        channel=ChannelType.WEB,
        content=[ContentPart(type="text", text=text)],
        received_at=datetime.now(UTC),
    )


def _agent(
    system: str = "be terse",
    budget: TurnBudget | None = None,
) -> AgentConfig:
    return AgentConfig(
        name="support",
        model="gpt-4o-mini",
        system_prompt=system,
        budget=budget or TurnBudget(),
    )


# ---------------------------------------------------------------------------
# Single-pass behaviour (regression from S008)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streams_tokens_then_complete() -> None:
    gw = _FakeGateway(
        [
            GatewayDelta(text="Hi"),
            GatewayDelta(text=" there"),
            GatewayDone(usage=Usage(input_tokens=5, output_tokens=2), cost_usd=0.01),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event())]

    types = [e.type for e in out]
    assert types == ["token", "token", "complete"]
    assert [e.payload["text"] for e in out if e.type == "token"] == ["Hi", " there"]
    assert out[-1].payload["content"][0]["text"] == "Hi there"


@pytest.mark.asyncio
async def test_request_includes_system_and_user_messages() -> None:
    gw = _FakeGateway([GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)])
    executor = TurnExecutor(gateway=gw)
    [_ async for _ in executor.execute(_agent(system="ROLE"), _event(text="ping"))]

    assert gw.last_request is not None
    roles = [m.role for m in gw.last_request.messages]
    contents = [m.content for m in gw.last_request.messages]
    assert roles == ["system", "user"]
    assert contents == ["ROLE", "ping"]


@pytest.mark.asyncio
async def test_request_id_overrides_default() -> None:
    gw = _FakeGateway([GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)])
    executor = TurnExecutor(gateway=gw)
    [_ async for _ in executor.execute(_agent(), _event(), request_id="caller-pinned-id")]
    assert gw.last_request is not None
    # Per-iteration suffix is deterministic so retries hit the cache.
    assert gw.last_request.request_id == "caller-pinned-id:i0"


@pytest.mark.asyncio
async def test_workspace_id_propagates_to_gateway_request() -> None:
    gw = _FakeGateway([GatewayDone(usage=Usage(input_tokens=0, output_tokens=0), cost_usd=0.0)])
    executor = TurnExecutor(gateway=gw)
    event = _event()
    [_ async for _ in executor.execute(_agent(), event)]
    assert gw.last_request is not None
    assert gw.last_request.workspace_id == str(event.workspace_id)


@pytest.mark.asyncio
async def test_emits_degrade_when_done_cost_exceeds_budget() -> None:
    gw = _FakeGateway(
        [
            GatewayDelta(text="ok"),
            GatewayDone(usage=Usage(input_tokens=10, output_tokens=10), cost_usd=99.0),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [
        e async for e in executor.execute(_agent(budget=TurnBudget(max_cost_usd=0.10)), _event())
    ]
    types = [e.type for e in out]
    assert "degrade" in types
    degrade = next(e for e in out if e.type == "degrade")
    assert degrade.payload["reason"] == "budget"
    assert types[-1] == "complete"


@pytest.mark.asyncio
async def test_gateway_error_emits_degrade_then_complete() -> None:
    gw = _FakeGateway([GatewayError(code="GW-PARSE", message="bad json")])
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event())]
    types = [e.type for e in out]
    assert types == ["degrade", "complete"]
    assert out[0].payload["reason"].startswith("gateway:GW-PARSE")


@pytest.mark.asyncio
async def test_emits_otel_span_with_required_attrs() -> None:
    from loop.observability import reset_for_test

    exporter = reset_for_test()
    gw = _FakeGateway(
        [
            GatewayDelta(text="hi"),
            GatewayDone(usage=Usage(input_tokens=7, output_tokens=3), cost_usd=0.02),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    event = _event()
    [_ async for _ in executor.execute(_agent(), event)]

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    span = finished[0]
    assert span.name == "turn.execute"
    attrs = dict(span.attributes or {})
    assert attrs["loop.span.kind"] == "llm"
    assert attrs["workspace_id"] == str(event.workspace_id)
    assert attrs["agent_id"] == "support"
    assert attrs["model"] == "gpt-4o-mini"
    assert attrs["input_tokens"] == 7
    assert attrs["output_tokens"] == 3
    assert attrs["cost_usd"] == pytest.approx(0.02)
    assert attrs["loop.turn.iterations"] == 1


# ---------------------------------------------------------------------------
# S012: multi-iteration with parallel tool dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_calls_are_dispatched_in_parallel_then_resolved() -> None:
    """Two tool calls in iter 0 -> both dispatched concurrently -> iter 1 streams text."""

    # Each tool waits on its own event, then sets its 'done' event. We
    # verify both ran before either finished by checking that both
    # 'started' events were set before either 'done' was set.
    started_a = asyncio.Event()
    started_b = asyncio.Event()
    release = asyncio.Event()

    async def tool_a(args: dict[str, Any]) -> str:
        started_a.set()
        await asyncio.wait_for(release.wait(), timeout=1.0)
        return f"a={args['x']}"

    async def tool_b(args: dict[str, Any]) -> str:
        started_b.set()
        # Once both have started, release everyone simultaneously.
        if started_a.is_set():
            release.set()
        else:
            await asyncio.wait_for(started_a.wait(), timeout=1.0)
            release.set()
        return f"b={args['y']}"

    registry = _FakeRegistry({"tool_a": tool_a, "tool_b": tool_b})

    gw = _ScriptedGateway(
        [
            [
                GatewayDelta(text="thinking..."),
                GatewayDone(
                    usage=Usage(input_tokens=10, output_tokens=2),
                    cost_usd=0.01,
                    tool_calls=(
                        ToolCall(id="c1", name="tool_a", arguments={"x": 1}),
                        ToolCall(id="c2", name="tool_b", arguments={"y": 2}),
                    ),
                ),
            ],
            [
                GatewayDelta(text="done!"),
                GatewayDone(
                    usage=Usage(input_tokens=20, output_tokens=2),
                    cost_usd=0.02,
                ),
            ],
        ]
    )

    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event(), tools=registry)]

    types = [e.type for e in out]
    assert types == [
        "token",
        "tool_call_start",
        "tool_call_start",
        "tool_call_end",
        "tool_call_end",
        "token",
        "complete",
    ]

    # Both tools were actually called with the right args.
    assert sorted(registry.calls_made) == [
        ("tool_a", {"x": 1}),
        ("tool_b", {"y": 2}),
    ]

    # Iteration 1 must include the assistant tool_calls turn + both tool messages.
    iter1 = gw.requests_seen[1]
    roles = [m.role for m in iter1.messages]
    assert roles == ["system", "user", "assistant", "tool", "tool"]
    tool_msgs = [m for m in iter1.messages if m.role == "tool"]
    assert {m.tool_call_id for m in tool_msgs} == {"c1", "c2"}
    assert {m.content for m in tool_msgs} == {"a=1", "b=2"}

    final = out[-1]
    assert final.payload["content"][0]["text"] == "thinking...done!"


@pytest.mark.asyncio
async def test_tool_failure_surfaces_as_tool_result_error_and_continues() -> None:
    """A raising tool does not stop sibling tools or the next iteration."""

    async def boom(_args: dict[str, Any]) -> str:
        raise RuntimeError("kaboom")

    async def ok(_args: dict[str, Any]) -> str:
        return "fine"

    registry = _FakeRegistry({"boom": boom, "ok": ok})

    gw = _ScriptedGateway(
        [
            [
                GatewayDone(
                    usage=Usage(input_tokens=1, output_tokens=1),
                    cost_usd=0.0,
                    tool_calls=(
                        ToolCall(id="c1", name="boom", arguments={}),
                        ToolCall(id="c2", name="ok", arguments={}),
                    ),
                ),
            ],
            [
                GatewayDelta(text="recovered"),
                GatewayDone(usage=Usage(input_tokens=1, output_tokens=1), cost_usd=0.0),
            ],
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event(), tools=registry)]

    tool_results = [e for e in out if e.type == "tool_call_end"]
    assert len(tool_results) == 2
    by_id = {r.payload["id"]: r.payload for r in tool_results}
    assert by_id["c1"]["error"] is not None and "kaboom" in by_id["c1"]["error"]
    assert by_id["c2"]["error"] is None and by_id["c2"]["result"] == "fine"

    # Iter 1 sees the failed tool's content prefixed with ERROR:.
    iter1 = gw.requests_seen[1]
    failure_msg = next(m for m in iter1.messages if m.tool_call_id == "c1")
    assert failure_msg.content.startswith("ERROR: RuntimeError")

    # Turn still completes cleanly (no degrade).
    types = [e.type for e in out]
    assert "degrade" not in types
    assert types[-1] == "complete"


@pytest.mark.asyncio
async def test_max_iterations_degrade_when_model_keeps_calling_tools() -> None:
    async def loop_tool(_args: dict[str, Any]) -> str:
        return "ok"

    registry = _FakeRegistry({"loop_tool": loop_tool})

    # Every iteration the model asks again for the same tool.
    repeating_iter: list[GatewayEvent] = [
        GatewayDone(
            usage=Usage(input_tokens=1, output_tokens=1),
            cost_usd=0.0,
            tool_calls=(ToolCall(id="cN", name="loop_tool", arguments={}),),
        ),
    ]
    gw = _ScriptedGateway([list(repeating_iter) for _ in range(2)])
    executor = TurnExecutor(gateway=gw)

    out = [
        e
        async for e in executor.execute(
            _agent(
                budget=TurnBudget(max_iterations=2),
            ),
            _event(),
            tools=registry,
        )
    ]
    degrades = [e for e in out if e.type == "degrade"]
    assert len(degrades) == 1
    assert degrades[0].payload["reason"] == "max_iterations"
    assert out[-1].type == "complete"
    assert len(gw.requests_seen) == 2  # exactly max_iterations calls


@pytest.mark.asyncio
async def test_tool_calls_without_registry_degrades() -> None:
    """If the model emits tool_calls but the agent has no registry, degrade."""

    gw = _FakeGateway(
        [
            GatewayDone(
                usage=Usage(input_tokens=1, output_tokens=1),
                cost_usd=0.0,
                tool_calls=(ToolCall(id="c1", name="ghost", arguments={}),),
            ),
        ]
    )
    executor = TurnExecutor(gateway=gw)
    out = [e async for e in executor.execute(_agent(), _event())]
    types = [e.type for e in out]
    assert types == ["degrade", "complete"]
    assert out[0].payload["reason"] == "tool_calls_without_registry"


@pytest.mark.asyncio
async def test_tool_specs_forwarded_to_gateway_request() -> None:
    """The agent's registry must advertise its tools to the gateway."""

    async def echo(args: dict[str, Any]) -> str:
        return str(args)

    registry = _FakeRegistry(
        {"echo": echo},
        specs=[
            ToolSpec(
                name="echo",
                description="echo input",
                input_schema={
                    "type": "object",
                    "properties": {"msg": {"type": "string"}},
                    "required": ["msg"],
                },
            )
        ],
    )
    gw = _FakeGateway([GatewayDone(usage=Usage(input_tokens=1, output_tokens=1), cost_usd=0.0)])
    executor = TurnExecutor(gateway=gw)
    [_ async for _ in executor.execute(_agent(), _event(), tools=registry)]

    assert gw.last_request is not None
    assert len(gw.last_request.tools) == 1
    assert gw.last_request.tools[0].name == "echo"
    assert gw.last_request.tools[0].input_schema["required"] == ["msg"]
