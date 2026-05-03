"""Workflow and script checks for the S654 voice p50 gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.voice_perf import VoicePerfSample, main, run_voice_perf

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
    assert payload["sample_count"] == 100
    assert len(payload["samples"]) == 100
    assert payload["sample_sources"] == ["synthetic:s908-cassette-replay-no-live-credentials"]
    assert payload["samples"][0]["source"].startswith("synthetic:")
    assert payload["p50_ms"] <= 700
    assert payload["passed"] is True


def test_voice_perf_script_fails_when_threshold_is_breached(tmp_path: Path) -> None:
    output = tmp_path / "voice_perf.json"

    assert main(["--output", str(output), "--iterations", "10", "--target-p50-ms", "10"]) == 2

    payload = json.loads(output.read_text())
    assert payload["passed"] is False
    assert payload["p50_ms"] > payload["target_p50_ms"]


def test_voice_perf_can_evaluate_real_sample_file(tmp_path: Path) -> None:
    samples = tmp_path / "samples.json"
    samples.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "turn_id": "live-1",
                        "source": "live:deepgram-agent-elevenlabs",
                        "stage_ms": {
                            "network_in": 20,
                            "asr_final": 140,
                            "agent": 240,
                            "tts_first_byte": 130,
                            "network_out": 20,
                        },
                    }
                ]
            }
        )
    )
    output = tmp_path / "voice_perf.json"

    assert main(["--samples", str(samples), "--output", str(output), "--target-p50-ms", "700"]) == 0

    payload = json.loads(output.read_text())
    assert payload["iterations"] == 1
    assert payload["sample_sources"] == ["live:deepgram-agent-elevenlabs"]
    assert payload["p50_ms"] == 550


def test_voice_perf_rejects_samples_without_source() -> None:
    sample = VoicePerfSample(
        turn_id="bad",
        source="synthetic:ok",
        stage_ms={
            "network_in": 1,
            "asr_final": 1,
            "agent": 1,
            "tts_first_byte": 1,
            "network_out": 1,
        },
    )
    assert run_voice_perf(samples=(sample,)).passed is True

    try:
        VoicePerfSample(turn_id="bad", source="", stage_ms={"agent": 1})
    except ValueError as exc:
        assert "sample source required" in str(exc)
    else:  # pragma: no cover - defensive assertion clarity
        raise AssertionError("missing sample source should fail")


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
    assert payload["sample_count"] == 100
    assert payload["sample_sources"]
    assert payload["p50_ms"] <= 700
    assert payload["passed"] is True
    assert "700 ms" in docs
    assert "scripts/voice_perf.py" in docs
    assert run_voice_perf().passed is True
