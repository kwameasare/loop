"""Multi-agent v0: Supervisor + Pipeline patterns.

This module intentionally sits *above* :mod:`turn_executor` rather
than inside it. A "sub-agent" is anything that satisfies the
:class:`AgentRunner` Protocol -- a single coroutine that maps a
text request to a text response. In production a runner is usually
backed by a :class:`TurnExecutor`, but tests can pass plain
in-process functions, which is what every test in this module does.

Two composition primitives are shipped here:

* :class:`Supervisor` -- given a *router* callable, picks exactly
  one sub-agent per request and forwards the request to it.
* :class:`Pipeline` -- chains N sub-agents in order; the output
  of step *i* is the input of step *i+1*.

Both record a structured :class:`HandoffTrail` so callers can show
"who did what" in the Studio replay UI later.

Cycles, parallel fan-out and the ``AgentGraph`` primitive land in
S042; this module is deliberately small and stateless.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MultiAgentError(RuntimeError):
    """Raised on multi-agent composition errors (unknown route, empty
    pipeline, etc.). A distinct exception type lets the runtime emit
    a structured ``error`` frame instead of bubbling a bare RuntimeError."""


class AgentSpec(_StrictModel):
    """Describes a single sub-agent for composition.

    The ``name`` is the routing key used by Supervisor and the
    label used by Pipeline. The runner is *not* part of the model
    -- AgentSpec is a frozen pydantic model and therefore must be
    JSON-serialisable; runners live alongside the spec in a
    ``dict[str, AgentRunner]`` map passed to the composer.
    """

    name: str = Field(min_length=1)
    description: str = ""


@runtime_checkable
class AgentRunner(Protocol):
    """Anything that can answer one request."""

    async def run(self, request: str) -> str: ...


class CallableRunner:
    """Trivially adapts an ``async def fn(str) -> str`` to AgentRunner."""

    def __init__(self, fn: Callable[[str], Awaitable[str]]) -> None:
        self._fn = fn

    async def run(self, request: str) -> str:
        return await self._fn(request)


# ---------------------------------------------------------------- Supervisor


Router = Callable[[str, Sequence[AgentSpec]], Awaitable[str]]


class HandoffStep(_StrictModel):
    """A single (agent_name, request, response) triple."""

    agent: str
    request: str
    response: str


class HandoffTrail(_StrictModel):
    """Ordered list of HandoffSteps describing a multi-agent run.

    Both Supervisor and Pipeline produce a HandoffTrail; the Studio
    replay screen renders this directly.
    """

    steps: tuple[HandoffStep, ...] = ()

    def with_step(self, step: HandoffStep) -> HandoffTrail:
        return HandoffTrail(steps=(*self.steps, step))


class MultiAgentResult(_StrictModel):
    """Result of running a Supervisor or Pipeline."""

    output: str
    trail: HandoffTrail


class Supervisor:
    """Routes one request to exactly one sub-agent.

    The ``router`` is invoked with the inbound request and the full
    list of available specs and must return the ``name`` of the
    chosen spec. Returning a name that does not appear in the spec
    list raises :class:`MultiAgentError`.
    """

    def __init__(
        self,
        *,
        specs: Iterable[AgentSpec],
        runners: dict[str, AgentRunner],
        router: Router,
    ) -> None:
        self._specs = tuple(specs)
        if not self._specs:
            raise MultiAgentError("Supervisor requires at least one AgentSpec")
        seen: set[str] = set()
        for spec in self._specs:
            if spec.name in seen:
                raise MultiAgentError(f"duplicate AgentSpec name: {spec.name!r}")
            seen.add(spec.name)
            if spec.name not in runners:
                raise MultiAgentError(
                    f"AgentSpec {spec.name!r} has no runner in the runners map"
                )
        self._runners = dict(runners)
        self._router = router

    @property
    def specs(self) -> tuple[AgentSpec, ...]:
        return self._specs

    async def run(self, request: str) -> MultiAgentResult:
        choice = await self._router(request, self._specs)
        if choice not in self._runners:
            valid = sorted(self._runners)
            raise MultiAgentError(
                f"router returned unknown agent {choice!r}; valid: {valid}"
            )
        response = await self._runners[choice].run(request)
        trail = HandoffTrail().with_step(
            HandoffStep(agent=choice, request=request, response=response)
        )
        return MultiAgentResult(output=response, trail=trail)


# ------------------------------------------------------------------ Pipeline


class Pipeline:
    """Sequential chain of sub-agents.

    The output of step *i* is the input of step *i+1*. A pipeline
    with zero specs raises :class:`MultiAgentError` at construction
    time -- there is no defensible default behaviour for an empty
    pipeline.
    """

    def __init__(
        self,
        *,
        specs: Sequence[AgentSpec],
        runners: dict[str, AgentRunner],
    ) -> None:
        if not specs:
            raise MultiAgentError("Pipeline requires at least one AgentSpec")
        for spec in specs:
            if spec.name not in runners:
                raise MultiAgentError(
                    f"AgentSpec {spec.name!r} has no runner in the runners map"
                )
        self._specs = tuple(specs)
        self._runners = dict(runners)

    @property
    def specs(self) -> tuple[AgentSpec, ...]:
        return self._specs

    async def run(self, request: str) -> MultiAgentResult:
        trail = HandoffTrail()
        current = request
        for spec in self._specs:
            response = await self._runners[spec.name].run(current)
            trail = trail.with_step(
                HandoffStep(agent=spec.name, request=current, response=response)
            )
            current = response
        return MultiAgentResult(output=current, trail=trail)


__all__ = [
    "AgentRunner",
    "AgentSpec",
    "CallableRunner",
    "HandoffStep",
    "HandoffTrail",
    "MultiAgentError",
    "MultiAgentResult",
    "Pipeline",
    "Router",
    "Supervisor",
]
