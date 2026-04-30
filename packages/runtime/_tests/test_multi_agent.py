"""Tests for the multi-agent v0 module: Supervisor + Pipeline."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from loop_runtime import (
    AgentSpec,
    CallableRunner,
    MultiAgentError,
    Pipeline,
    Supervisor,
)


def _runners(**fns: object) -> dict:
    out: dict = {}
    for name, fn in fns.items():
        async def _wrap(req: str, *, _fn=fn) -> str:
            return _fn(req)  # type: ignore[operator]
        out[name] = CallableRunner(_wrap)
    return out


def test_agent_spec_requires_name() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AgentSpec(name="")


@pytest.mark.asyncio
async def test_supervisor_routes_to_chosen_agent() -> None:
    specs = [
        AgentSpec(name="billing", description="answers billing questions"),
        AgentSpec(name="tech", description="answers tech questions"),
    ]
    runners = _runners(
        billing=lambda r: f"billing:{r}",
        tech=lambda r: f"tech:{r}",
    )

    async def router(req: str, specs: Sequence[AgentSpec]) -> str:
        return "billing" if "invoice" in req else "tech"

    sup = Supervisor(specs=specs, runners=runners, router=router)
    result = await sup.run("how do I see my invoice?")
    assert result.output == "billing:how do I see my invoice?"
    assert len(result.trail.steps) == 1
    assert result.trail.steps[0].agent == "billing"


@pytest.mark.asyncio
async def test_supervisor_raises_on_unknown_route() -> None:
    specs = [AgentSpec(name="a")]
    runners = _runners(a=lambda r: r)

    async def router(req: str, specs: Sequence[AgentSpec]) -> str:
        return "ghost"

    sup = Supervisor(specs=specs, runners=runners, router=router)
    with pytest.raises(MultiAgentError, match="unknown agent"):
        await sup.run("hi")


def test_supervisor_rejects_missing_runner() -> None:
    with pytest.raises(MultiAgentError, match="no runner"):
        Supervisor(
            specs=[AgentSpec(name="a"), AgentSpec(name="b")],
            runners=_runners(a=lambda r: r),
            router=lambda req, specs: "a",  # type: ignore[arg-type, return-value]
        )


def test_supervisor_rejects_duplicate_spec_names() -> None:
    with pytest.raises(MultiAgentError, match="duplicate"):
        Supervisor(
            specs=[AgentSpec(name="a"), AgentSpec(name="a")],
            runners=_runners(a=lambda r: r),
            router=lambda req, specs: "a",  # type: ignore[arg-type, return-value]
        )


def test_supervisor_rejects_empty_specs() -> None:
    async def router(req: str, specs: Sequence[AgentSpec]) -> str:
        return ""

    with pytest.raises(MultiAgentError, match="at least one"):
        Supervisor(specs=[], runners={}, router=router)


@pytest.mark.asyncio
async def test_pipeline_chains_outputs() -> None:
    specs = [AgentSpec(name="upper"), AgentSpec(name="exclaim")]
    runners = _runners(
        upper=lambda r: r.upper(),
        exclaim=lambda r: r + "!",
    )
    pipe = Pipeline(specs=specs, runners=runners)
    result = await pipe.run("hi")
    assert result.output == "HI!"
    assert [s.agent for s in result.trail.steps] == ["upper", "exclaim"]
    assert result.trail.steps[0].request == "hi"
    assert result.trail.steps[0].response == "HI"
    assert result.trail.steps[1].request == "HI"
    assert result.trail.steps[1].response == "HI!"


def test_pipeline_rejects_empty_specs() -> None:
    with pytest.raises(MultiAgentError, match="at least one"):
        Pipeline(specs=[], runners={})


def test_pipeline_rejects_missing_runner() -> None:
    with pytest.raises(MultiAgentError, match="no runner"):
        Pipeline(specs=[AgentSpec(name="x")], runners={})


@pytest.mark.asyncio
async def test_handoff_trail_is_immutable() -> None:
    from loop_runtime import HandoffStep, HandoffTrail

    trail = HandoffTrail()
    new = trail.with_step(HandoffStep(agent="a", request="hi", response="ho"))
    assert trail.steps == ()
    assert len(new.steps) == 1
