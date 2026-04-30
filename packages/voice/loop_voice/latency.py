"""Latency budgets and measurement for the voice pipeline.

The voice pipeline is the most latency-sensitive surface in Loop:
sub-second turn-around is table stakes for natural conversation.
This module captures the per-stage budget, gives the runtime a
:class:`LatencyTracker` to record measurements, and exposes
percentile + budget-breach helpers so we can fail CI when a build
slips below target.

Default budget (S048):

  | Stage                  | p50 ms | p95 ms |
  | ---------------------- | -----: | -----: |
  | network ingress        |     20 |     45 |
  | ASR final transcript   |    160 |    280 |
  | agent + tool decision  |    280 |    520 |
  | TTS first audio byte   |    160 |    260 |
  | network egress         |     20 |     45 |
  | **end-to-end p50/p95** |    640 |   1150 |

The end-to-end p50 budget is **640 ms**, leaving headroom under
the 700 ms public commitment. p95 caps at 1150 ms (also under
the 1.2 s soft commitment from PERFORMANCE.md).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class LatencyStage(StrEnum):
    """The six measurable stages of one voice turn."""

    NETWORK_IN = "network_in"
    ASR_FINAL = "asr_final"
    AGENT = "agent"
    TTS_FIRST_BYTE = "tts_first_byte"
    NETWORK_OUT = "network_out"


class StageBudget(_StrictModel):
    p50_ms: float = Field(gt=0)
    p95_ms: float = Field(gt=0)


class LatencyBudget(_StrictModel):
    """Per-stage and end-to-end latency budgets in milliseconds."""

    stages: dict[LatencyStage, StageBudget]
    end_to_end_p50_ms: float = Field(gt=0)
    end_to_end_p95_ms: float = Field(gt=0)


DEFAULT_BUDGET = LatencyBudget(
    stages={
        LatencyStage.NETWORK_IN: StageBudget(p50_ms=20, p95_ms=45),
        LatencyStage.ASR_FINAL: StageBudget(p50_ms=160, p95_ms=280),
        LatencyStage.AGENT: StageBudget(p50_ms=280, p95_ms=520),
        LatencyStage.TTS_FIRST_BYTE: StageBudget(p50_ms=160, p95_ms=260),
        LatencyStage.NETWORK_OUT: StageBudget(p50_ms=20, p95_ms=45),
    },
    end_to_end_p50_ms=640,
    end_to_end_p95_ms=1150,
)
"""Sprint-1 budget; reviewed at every release train."""


class LatencyMeasurement(_StrictModel):
    """One observed turn, broken down by stage."""

    turn_id: str = Field(min_length=1)
    stage_ms: dict[LatencyStage, float]

    @property
    def total_ms(self) -> float:
        return sum(self.stage_ms.values())


class BudgetBreach(_StrictModel):
    """A single stage (or the end-to-end total) that overshot."""

    stage: LatencyStage | None  # None => end-to-end total
    percentile: str             # "p50" | "p95"
    observed_ms: float
    budget_ms: float

    @property
    def over_ms(self) -> float:
        return self.observed_ms - self.budget_ms


def _percentile(values: Iterable[float], *, p: float) -> float:
    """Linear-interpolation percentile (p in [0, 1])."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot compute percentile of empty sequence")
    if len(ordered) == 1:
        return ordered[0]
    pos = p * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


class LatencyTracker:
    """Process-local accumulator for :class:`LatencyMeasurement`."""

    def __init__(self) -> None:
        self._measurements: list[LatencyMeasurement] = []

    def record(self, measurement: LatencyMeasurement) -> None:
        self._measurements.append(measurement)

    def __len__(self) -> int:
        return len(self._measurements)

    def percentiles(
        self, stage: LatencyStage | None = None
    ) -> Mapping[str, float]:
        """Return ``{"p50": ..., "p95": ...}`` for one stage or end-to-end."""
        if not self._measurements:
            raise ValueError("no measurements recorded")
        if stage is None:
            samples = [m.total_ms for m in self._measurements]
        else:
            samples = [
                m.stage_ms[stage]
                for m in self._measurements
                if stage in m.stage_ms
            ]
            if not samples:
                raise ValueError(f"no measurements for stage {stage!r}")
        return {
            "p50": _percentile(samples, p=0.5),
            "p95": _percentile(samples, p=0.95),
        }

    def breaches(
        self, budget: LatencyBudget = DEFAULT_BUDGET
    ) -> tuple[BudgetBreach, ...]:
        """Return every stage/percentile that exceeds the supplied budget."""
        if not self._measurements:
            return ()
        out: list[BudgetBreach] = []
        for stage, sb in budget.stages.items():
            samples = [
                m.stage_ms[stage]
                for m in self._measurements
                if stage in m.stage_ms
            ]
            if not samples:
                continue
            p50 = _percentile(samples, p=0.5)
            p95 = _percentile(samples, p=0.95)
            if p50 > sb.p50_ms:
                out.append(
                    BudgetBreach(
                        stage=stage,
                        percentile="p50",
                        observed_ms=p50,
                        budget_ms=sb.p50_ms,
                    )
                )
            if p95 > sb.p95_ms:
                out.append(
                    BudgetBreach(
                        stage=stage,
                        percentile="p95",
                        observed_ms=p95,
                        budget_ms=sb.p95_ms,
                    )
                )
        e2e = self.percentiles(stage=None)
        if e2e["p50"] > budget.end_to_end_p50_ms:
            out.append(
                BudgetBreach(
                    stage=None,
                    percentile="p50",
                    observed_ms=e2e["p50"],
                    budget_ms=budget.end_to_end_p50_ms,
                )
            )
        if e2e["p95"] > budget.end_to_end_p95_ms:
            out.append(
                BudgetBreach(
                    stage=None,
                    percentile="p95",
                    observed_ms=e2e["p95"],
                    budget_ms=budget.end_to_end_p95_ms,
                )
            )
        return tuple(out)


__all__ = [
    "DEFAULT_BUDGET",
    "BudgetBreach",
    "LatencyBudget",
    "LatencyMeasurement",
    "LatencyStage",
    "LatencyTracker",
    "StageBudget",
]
