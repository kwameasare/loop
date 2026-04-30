"""Canary-promotion FSM (S267).

A canary deploy gradually shifts traffic from the previous version
(``stable``) to a new version (``candidate``):

    PROVISIONED -> CANARY_10 -> CANARY_50 -> PROMOTED
                       \\           \\
                        \\           +--> ROLLED_BACK (auto on regression)
                         +-> ROLLED_BACK

Each transition is gated by a :class:`CanaryHealth` snapshot:

* ``error_rate`` must be <= ``max_error_rate``
* ``p95_latency_ms`` must be <= ``max_p95_latency_ms``
* the candidate must have served at least ``min_samples`` requests

If health fails, the FSM transitions to ``ROLLED_BACK`` and emits a
:class:`CanaryEvent` with kind ``REGRESSION``. The deploy controller
(S266) drives the FSM by calling :meth:`step` on a fixed cadence and
stops when the FSM reports terminal.

The FSM is pure, synchronous, and decision-only — it does not call
the load balancer. The caller pairs each ``step`` result with a
side-effect that adjusts traffic split (or, in tests, asserts the
expected sequence).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "STAGE_ORDER",
    "STAGE_TRAFFIC",
    "CanaryDecision",
    "CanaryEvent",
    "CanaryEventKind",
    "CanaryFSM",
    "CanaryHealth",
    "CanaryPolicy",
    "CanaryStage",
]


class CanaryStage(StrEnum):
    PROVISIONED = "provisioned"
    CANARY_10 = "canary_10"
    CANARY_50 = "canary_50"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


STAGE_ORDER: tuple[CanaryStage, ...] = (
    CanaryStage.PROVISIONED,
    CanaryStage.CANARY_10,
    CanaryStage.CANARY_50,
    CanaryStage.PROMOTED,
)

# Canary stage -> percentage of live traffic served by the candidate.
STAGE_TRAFFIC: dict[CanaryStage, int] = {
    CanaryStage.PROVISIONED: 0,
    CanaryStage.CANARY_10: 10,
    CanaryStage.CANARY_50: 50,
    CanaryStage.PROMOTED: 100,
    CanaryStage.ROLLED_BACK: 0,
}

TERMINAL_STAGES: frozenset[CanaryStage] = frozenset(
    {CanaryStage.PROMOTED, CanaryStage.ROLLED_BACK}
)


class CanaryPolicy(BaseModel):
    """Promotion gate thresholds. Frozen so a policy snapshot is
    captured at submit time."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    max_error_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    max_p95_latency_ms: int = Field(default=1500, ge=1)
    min_samples: int = Field(default=100, ge=1)


class CanaryHealth(BaseModel):
    """Per-step observed health of the candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    samples: int = Field(ge=0)
    error_rate: float = Field(ge=0.0, le=1.0)
    p95_latency_ms: int = Field(ge=0)


class CanaryEventKind(StrEnum):
    PROMOTED_TO = "promoted_to"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    REGRESSION = "regression"
    NO_CHANGE = "no_change"


class CanaryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: CanaryEventKind
    from_stage: CanaryStage
    to_stage: CanaryStage
    reason: str = ""
    at: datetime


class CanaryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    stage: CanaryStage
    traffic_pct: int = Field(ge=0, le=100)
    terminal: bool
    event: CanaryEvent


class CanaryFSM:
    """Deterministic canary FSM. One instance per active canary."""

    def __init__(self, *, policy: CanaryPolicy | None = None) -> None:
        self._policy = policy or CanaryPolicy()
        self._stage: CanaryStage = CanaryStage.PROVISIONED
        self._history: list[CanaryEvent] = []

    @property
    def stage(self) -> CanaryStage:
        return self._stage

    @property
    def policy(self) -> CanaryPolicy:
        return self._policy

    @property
    def history(self) -> Sequence[CanaryEvent]:
        return tuple(self._history)

    @property
    def terminal(self) -> bool:
        return self._stage in TERMINAL_STAGES

    def step(self, health: CanaryHealth, *, now: datetime | None = None) -> CanaryDecision:
        ts = now or datetime.now(UTC)

        if self.terminal:
            event = self._record(
                CanaryEventKind.NO_CHANGE,
                self._stage,
                self._stage,
                reason="terminal",
                at=ts,
            )
            return CanaryDecision(
                stage=self._stage,
                traffic_pct=STAGE_TRAFFIC[self._stage],
                terminal=True,
                event=event,
            )

        # Regression check: any breach => immediate rollback, regardless
        # of sample count. A blowup at 10% traffic is a blowup.
        if (
            health.error_rate > self._policy.max_error_rate
            or health.p95_latency_ms > self._policy.max_p95_latency_ms
        ):
            return self._rollback(health, ts)

        if health.samples < self._policy.min_samples:
            event = self._record(
                CanaryEventKind.INSUFFICIENT_SAMPLES,
                self._stage,
                self._stage,
                reason=f"samples={health.samples} < {self._policy.min_samples}",
                at=ts,
            )
            return CanaryDecision(
                stage=self._stage,
                traffic_pct=STAGE_TRAFFIC[self._stage],
                terminal=False,
                event=event,
            )

        next_stage = _next_stage(self._stage)
        event = self._record(
            CanaryEventKind.PROMOTED_TO,
            self._stage,
            next_stage,
            reason=(
                f"samples={health.samples} err={health.error_rate:.4f} "
                f"p95={health.p95_latency_ms}ms"
            ),
            at=ts,
        )
        self._stage = next_stage
        return CanaryDecision(
            stage=self._stage,
            traffic_pct=STAGE_TRAFFIC[self._stage],
            terminal=self.terminal,
            event=event,
        )

    def force_rollback(self, *, reason: str, now: datetime | None = None) -> CanaryDecision:
        ts = now or datetime.now(UTC)
        if self.terminal:
            event = self._record(
                CanaryEventKind.NO_CHANGE,
                self._stage,
                self._stage,
                reason=reason or "terminal",
                at=ts,
            )
            return CanaryDecision(
                stage=self._stage,
                traffic_pct=STAGE_TRAFFIC[self._stage],
                terminal=True,
                event=event,
            )
        return self._rollback_with_reason(reason, ts)

    def _rollback(self, health: CanaryHealth, ts: datetime) -> CanaryDecision:
        reason = (
            f"err={health.error_rate:.4f}>max={self._policy.max_error_rate} "
            f"or p95={health.p95_latency_ms}>max={self._policy.max_p95_latency_ms}"
        )
        return self._rollback_with_reason(reason, ts)

    def _rollback_with_reason(self, reason: str, ts: datetime) -> CanaryDecision:
        prev = self._stage
        event = self._record(
            CanaryEventKind.REGRESSION,
            prev,
            CanaryStage.ROLLED_BACK,
            reason=reason,
            at=ts,
        )
        self._stage = CanaryStage.ROLLED_BACK
        return CanaryDecision(
            stage=self._stage,
            traffic_pct=STAGE_TRAFFIC[self._stage],
            terminal=True,
            event=event,
        )

    def _record(
        self,
        kind: CanaryEventKind,
        frm: CanaryStage,
        to: CanaryStage,
        *,
        reason: str,
        at: datetime,
    ) -> CanaryEvent:
        ev = CanaryEvent(kind=kind, from_stage=frm, to_stage=to, reason=reason, at=at)
        self._history.append(ev)
        return ev


def _next_stage(stage: CanaryStage) -> CanaryStage:
    if stage == CanaryStage.PROVISIONED:
        return CanaryStage.CANARY_10
    if stage == CanaryStage.CANARY_10:
        return CanaryStage.CANARY_50
    if stage == CanaryStage.CANARY_50:
        return CanaryStage.PROMOTED
    raise ValueError(f"no next stage from {stage}")
