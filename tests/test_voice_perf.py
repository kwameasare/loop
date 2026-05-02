"""Workflow and script checks for the S654 voice p50 gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.voice_perf import main, run_voice_perf

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "voice-perf.yml"
RESULT = ROOT / "bench" / "results" / "voice_perf.json"
DOC = ROOT / "docs" / "perf" / "voice_perf.md"


def test_voice_perf_script_writes_passing_report(tmp_path: Path) -> None:
    output = tmp_path / "voice_perf.json"

    assert main(["--output", str(output), "--iterations", "100", "--target-p50-ms", "700"]) == 0

    payload = json.loads(output.read_text())
    assert payload["name"] == "voice_perf_p50_gate"
    assert payload["iterations"] == 100
    assert payload["p50_ms"] <= 700
    assert payload["passed"] is True


def test_voice_perf_script_fails_when_threshold_is_breached(tmp_path: Path) -> None:
    output = tmp_path / "voice_perf.json"

    assert main(["--output", str(output), "--iterations", "10", "--target-p50-ms", "10"]) == 2

    payload = json.loads(output.read_text())
    assert payload["passed"] is False
    assert payload["p50_ms"] > payload["target_p50_ms"]


def test_voice_perf_workflow_runs_nightly_and_pages() -> None:
    data = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["voice-perf"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "17 6 * * *"
    assert "workflow_dispatch" in triggers
    assert "scripts/voice_perf.py" in runs
    assert "--target-p50-ms 700" in runs
    assert any(step.get("name") == "Upload voice performance report" for step in steps)
    assert any(
        step.get("name") == "Page on-call" and step.get("if") == "failure()" for step in steps
    )


def test_voice_perf_report_and_docs_are_published() -> None:
    payload = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert payload["name"] == "voice_perf_p50_gate"
    assert payload["p50_ms"] <= 700
    assert payload["passed"] is True
    assert "700 ms" in docs
    assert "scripts/voice_perf.py" in docs
    assert run_voice_perf().passed is True
