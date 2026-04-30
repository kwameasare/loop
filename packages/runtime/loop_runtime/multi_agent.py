"""Multi-agent v0 + GA: Supervisor + Pipeline + Parallel + AgentGraph.

This module intentionally sits *above* :mod:`turn_executor` rather
than inside it. A "sub-agent" is anything that satisfies the
:class:`AgentRunner` Protocol -- a single coroutine that maps a
text request to a text response. In production a runner is usually
backed by a :class:`TurnExecutor`, but tests can pass plain
in-process functions, which is what every test in this module does.

Composition primitives:

* :class:`Supervisor` -- given a *router* callable, picks exactly
  one sub-agent per request and forwards the request to it.
* :class:`Pipeline` -- chains N sub-agents in order; the output
  of step *i* is the input of step *i+1*.
* :class:`Parallel` -- fans out a request to N sub-agents
  concurrently and merges their responses with a user-supplied
  ``merger`` callable.
* :class:`AgentGraph` -- arbitrary directed (possibly cyclic) graph
  of agents with a ``Selector`` that drives the next hop based on
  the running state. A safety bound on iterations stops runaway
  cycles.

Both v0 and GA primitives record a structured :class:`HandoffTrail`
so callers can show "who did what" in the Studio replay UI.
"""

from __future__ import annotations

import asyncio
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
    "AgentGraph",
    "AgentRunner",
    "AgentSpec",
    "CallableRunner",
    "HandoffStep",
    "HandoffTrail",
    "Merger",
    "MultiAgentError",
    "MultiAgentResult",
    "Parallel",
    "Pipeline",
    "Router",
    "Selector",
    "Supervisor",
]


# -------------------------------------------------------------------- Parallel


Merger = Callable[[Sequence[tuple[str, str]]], Awaitable[str]]
"""Reduce ``[(agent_name, response), ...]`` into a single string."""


class Parallel:
    """Fans out one request to N sub-agents concurrently.

    All runners receive the same input. Their responses are merged
    by the user-supplied :data:`Merger` (e.g. concatenate, vote,
    pick-best). The :class:`HandoffTrail` records each runner's
    response in spec order regardless of completion order, so the
    trail is deterministic for replay.
    """

    def __init__(
        self,
        *,
        specs: Sequence[AgentSpec],
        runners: dict[str, AgentRunner],
        merger: Merger,
    ) -> None:
        if not specs:
            raise MultiAgentError("Parallel requires at least one AgentSpec")
        seen: set[str] = set()
        for spec in specs:
            if spec.name in seen:
                raise MultiAgentError(f"duplicate AgentSpec name: {spec.name!r}")
            seen.add(spec.name)
            if spec.name not in runners:
                raise MultiAgentError(
                    f"AgentSpec {spec.name!r} has no runner in the runners map"
                )
        self._specs = tuple(specs)
        self._runners = dict(runners)
        self._merger = merger

    @property
    def specs(self) -> tuple[AgentSpec, ...]:
        return self._specs

    async def run(self, request: str) -> MultiAgentResult:
        responses = await asyncio.gather(
            *(self._runners[spec.name].run(request) for spec in self._specs)
        )
        trail = HandoffTrail()
        pairs: list[tuple[str, str]] = []
        for spec, response in zip(self._specs, responses, strict=True):
            trail = trail.with_step(
                HandoffStep(agent=spec.name, request=request, response=response)
            )
            pairs.append((spec.name, response))
        merged = await self._merger(pairs)
        return MultiAgentResult(output=merged, trail=trail)


# ------------------------------------------------------------------ AgentGraph


Selector = Callable[[str, str, HandoffTrail], Awaitable[str | None]]
"""Pick the next agent given ``(last_agent, last_response, trail)``.

Returning ``None`` ends the graph traversal.
"""


class AgentGraph:
    """Directed graph of agents with a Selector-driven traversal.

    Construction takes a ``start`` agent name and a ``selector``
    coroutine. On each step the selector inspects the most recent
    response (and the full trail) and returns the next agent name,
    or ``None`` to terminate. Cycles are allowed; runaway cycles
    are bounded by ``max_steps`` (default 16) which raises
    :class:`MultiAgentError` if exceeded.

    The graph topology is implicit in the selector -- callers
    enforce edge constraints inside their selector function.
    """

    DEFAULT_MAX_STEPS = 16

    def __init__(
        self,
        *,
        specs: Iterable[AgentSpec],
        runners: dict[str, AgentRunner],
        selector: Selector,
        start: str,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        self._specs = tuple(specs)
        if not self._specs:
            raise MultiAgentError("AgentGraph requires at least one AgentSpec")
        seen: set[str] = set()
        for spec in self._specs:
            if spec.name in seen:
                raise MultiAgentError(f"duplicate AgentSpec name: {spec.name!r}")
            seen.add(spec.name)
            if spec.name not in runners:
                raise MultiAgentError(
                    f"AgentSpec {spec.name!r} has no runner in the runners map"
                )
        if start not in seen:
            raise MultiAgentError(f"start agent {start!r} not in specs")
        if max_steps < 1:
            raise MultiAgentError("max_steps must be >= 1")
        self._runners = dict(runners)
        self._selector = selector
        self._start = start
        self._max_steps = max_steps

    @property
    def specs(self) -> tuple[AgentSpec, ...]:
        return self._specs

    async def run(self, request: str) -> MultiAgentResult:
        trail = HandoffTrail()
        current_agent: str | None = self._start
        current_input = request
        last_response = ""
        step_count = 0
        while current_agent is not None:
            step_count += 1
            if step_count > self._max_steps:
                raise MultiAgentError(
                    f"AgentGraph exceeded max_steps={self._max_steps}"
                )
            if current_agent not in self._runners:
                raise MultiAgentError(
                    f"selector returned unknown agent {current_agent!r}"
                )
            response = await self._runners[current_agent].run(current_input)
            trail = trail.with_step(
                HandoffStep(
                    agent=current_agent,
                    request=current_input,
                    response=response,
                )
            )
            last_response = response
            current_input = response
            current_agent = await self._selector(current_agent, response, trail)
        return MultiAgentResult(output=last_response, trail=trail)
