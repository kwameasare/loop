"""Workflow and script checks for the S842 KB retrieval perf gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from loop_kb_engine.perf_fixture import DEFAULT_CHUNK_COUNT, SyntheticMillionChunkFixture

from scripts.kb_retrieval_perf import main, run_kb_retrieval_perf

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "kb-retrieval-perf.yml"
RESULT = ROOT / "bench" / "results" / "kb_retrieval_1m.json"
DOC = ROOT / "docs" / "perf" / "kb_retrieval_1m.md"


def test_synthetic_fixture_models_one_million_chunks() -> None:
    fixture = SyntheticMillionChunkFixture()

    hits = fixture.search("refund policy enterprise", top_k=5)

    assert fixture.chunk_count == DEFAULT_CHUNK_COUNT
    assert len(hits) == 5
    assert hits[0].chunk_id.startswith("chunk-")
    assert hits[0].score >= hits[-1].score


def test_synthetic_fixture_rejects_invalid_top_k() -> None:
    fixture = SyntheticMillionChunkFixture()

    with pytest.raises(ValueError, match="top_k"):
        fixture.search("refund policy", top_k=0)


def test_kb_retrieval_script_writes_passing_report(tmp_path: Path) -> None:
    output = tmp_path / "kb_retrieval_1m.json"

    assert main(["--output", str(output), "--iterations", "20", "--target-p50-ms", "200"]) == 0

    payload = json.loads(output.read_text())
    assert payload["name"] == "kb_retrieval_1m_chunks"
    assert payload["chunk_count"] == 1_000_000
    assert payload["p50_ms"] < 200
    assert payload["passed"] is True


def test_kb_retrieval_script_fails_when_threshold_is_breached(tmp_path: Path) -> None:
    output = tmp_path / "kb_retrieval_1m.json"

    assert main(["--output", str(output), "--iterations", "20", "--target-p50-ms", "0"]) == 2

    payload = json.loads(output.read_text())
    assert payload["passed"] is False


def test_kb_retrieval_workflow_runs_nightly_and_pages() -> None:
    data = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["kb-retrieval-perf"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "23 6 * * *"
    assert "workflow_dispatch" in triggers
    assert "scripts/kb_retrieval_perf.py" in runs
    assert "--target-p50-ms 200" in runs
    assert any(step.get("name") == "Upload KB retrieval report" for step in steps)
    assert any(
        step.get("name") == "Page on-call" and step.get("if") == "failure()" for step in steps
    )


def test_kb_retrieval_report_and_docs_are_published() -> None:
    payload = json.loads(RESULT.read_text())
    docs = DOC.read_text()

    assert payload["name"] == "kb_retrieval_1m_chunks"
    assert payload["chunk_count"] == DEFAULT_CHUNK_COUNT
    assert payload["p50_ms"] < 200
    assert payload["passed"] is True
    assert "1M chunks" in docs
    assert "scripts/kb_retrieval_perf.py" in docs
    assert run_kb_retrieval_perf(iterations=20).passed is True
