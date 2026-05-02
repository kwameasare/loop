"""Tests for the S142 runtime 100 turns/minute baseline."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "k6_runtime_baseline_100rpm.js"
RESULT = ROOT / "bench" / "results" / "runtime_baseline_100rpm.json"
DOC = ROOT / "docs" / "perf" / "runtime-baseline.md"


def test_runtime_baseline_k6_script_uses_100rpm_for_5_minutes() -> None:
    script = SCRIPT.read_text()

    assert "const BASELINE_RATE_PER_MINUTE = 100" in script
    assert 'executor: "constant-arrival-rate"' in script
    assert "rate: BASELINE_RATE_PER_MINUTE" in script
    assert 'timeUnit: "1m"' in script
    assert 'duration: "5m"' in script
    assert "/v1/turns" in script


def test_runtime_baseline_report_contains_required_latency_stats() -> None:
    result = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert result["name"] == "runtime_baseline_100rpm"
    assert result["stats"]["turns_per_minute"] == 100
    assert {"p50_ms", "p95_ms", "p99_ms", "error_rate"} <= set(result["stats"])
    assert "| p50 latency |" in docs
    assert "| p95 latency |" in docs
    assert "| p99 latency |" in docs
    assert "| error rate |" in docs
