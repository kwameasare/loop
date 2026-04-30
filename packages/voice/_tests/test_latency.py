"""Tests for the voice latency budget + tracker (S048)."""

from __future__ import annotations

import pytest
from loop_voice import (
    DEFAULT_BUDGET,
    LatencyMeasurement,
    LatencyStage,
    LatencyTracker,
)


def _measurement(turn_id: str, **stage_ms: float) -> LatencyMeasurement:
    return LatencyMeasurement(
        turn_id=turn_id,
        stage_ms={LatencyStage(k): v for k, v in stage_ms.items()},
    )


def test_default_budget_p50_under_seven_hundred() -> None:
    assert DEFAULT_BUDGET.end_to_end_p50_ms <= 700


def test_default_budget_stage_sums_under_e2e_target() -> None:
    p50_sum = sum(s.p50_ms for s in DEFAULT_BUDGET.stages.values())
    assert p50_sum <= DEFAULT_BUDGET.end_to_end_p50_ms


def test_tracker_percentiles_single_stage() -> None:
    tr = LatencyTracker()
    for i, t in enumerate([100, 110, 130, 160, 200]):
        tr.record(_measurement(f"t{i}", asr_final=t))
    pcts = tr.percentiles(stage=LatencyStage.ASR_FINAL)
    assert pcts["p50"] == pytest.approx(130)
    assert pcts["p95"] == pytest.approx(192, rel=0.05)


def test_tracker_end_to_end_percentiles() -> None:
    tr = LatencyTracker()
    for i, t in enumerate([500, 600, 640, 700, 800]):
        tr.record(_measurement(f"t{i}", agent=t))
    e2e = tr.percentiles()  # stage=None => end-to-end
    assert e2e["p50"] == pytest.approx(640)


def test_tracker_breaches_flag_overshoot() -> None:
    tr = LatencyTracker()
    # blow the agent stage budget on purpose
    for i in range(5):
        tr.record(
            _measurement(
                f"t{i}",
                network_in=20,
                asr_final=160,
                agent=600,  # over the 280 ms p50 budget
                tts_first_byte=160,
                network_out=20,
            )
        )
    breaches = tr.breaches()
    assert any(b.stage == LatencyStage.AGENT and b.percentile == "p50"
               for b in breaches)
    # end-to-end p50 also breached (sum of medians = 960)
    assert any(b.stage is None and b.percentile == "p50" for b in breaches)


def test_tracker_no_breaches_within_budget() -> None:
    tr = LatencyTracker()
    for i in range(5):
        tr.record(
            _measurement(
                f"t{i}",
                network_in=18,
                asr_final=150,
                agent=260,
                tts_first_byte=150,
                network_out=18,
            )
        )
    assert tr.breaches() == ()


def test_tracker_empty_raises() -> None:
    tr = LatencyTracker()
    with pytest.raises(ValueError, match="no measurements"):
        tr.percentiles()


def test_breach_over_ms_property() -> None:
    tr = LatencyTracker()
    tr.record(_measurement("t0", agent=500))
    breach = next(b for b in tr.breaches() if b.stage == LatencyStage.AGENT)
    assert breach.over_ms == pytest.approx(220)
