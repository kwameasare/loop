"""Tests for LangMem-style summarization (S822)."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from loop_memory import (
    SummaryEvalCase,
    evaluate_summary_retrieval,
    langmem_summarize,
)
from loop_memory.episodic import EpisodicError, auto_summarize


def _filler() -> str:
    return " ".join(["small talk about onboarding"] * 30)


def test_langmem_summarize_keeps_late_retrieval_anchors() -> None:
    messages = (
        _filler(),
        "User prefers eu-west region and needs Datadog SIEM webhook export.",
    )

    baseline = auto_summarize(messages, max_chars=100)
    candidate = langmem_summarize(messages, max_chars=120)

    assert "datadog" not in baseline.lower()
    assert "datadog" in candidate.lower()
    assert "webhook" in candidate.lower()
    assert len(candidate) <= 120


def test_langmem_summarize_blends_llm_summary_with_anchors() -> None:
    def fake_llm(messages: Sequence[str], *, max_chars: int) -> str:
        assert max_chars > 0
        assert messages
        return "Enterprise security recap"

    summary = langmem_summarize(
        (
            _filler(),
            "Customer needs PagerDuty integration and audit webhook routing.",
        ),
        max_chars=140,
        llm_summarizer=fake_llm,
    )

    assert "Enterprise security recap" in summary
    assert "integration" in summary
    assert "webhook" in summary


def test_summary_retrieval_ablation_shows_required_lift() -> None:
    cases = (
        SummaryEvalCase(
            messages=(
                _filler(),
                "Buyer needs Datadog SIEM webhook export for audit evidence.",
            ),
            query="datadog siem webhook export",
        ),
        SummaryEvalCase(
            messages=(
                _filler(),
                "Workspace must run in eu-west region with invoice billing.",
            ),
            query="eu-west region invoice billing",
        ),
    )

    report = evaluate_summary_retrieval(cases, max_chars=120)

    assert report.candidate_score > report.baseline_score
    assert report.relative_improvement >= 0.10
    assert report.passed is True


def test_summary_retrieval_ablation_rejects_bad_inputs() -> None:
    with pytest.raises(EpisodicError):
        evaluate_summary_retrieval(())
    with pytest.raises(EpisodicError):
        evaluate_summary_retrieval(
            (SummaryEvalCase(messages=("hello",), query="and the"),)
        )


def test_langmem_summarize_rejects_empty_and_bad_limits() -> None:
    with pytest.raises(EpisodicError):
        langmem_summarize(())
    with pytest.raises(EpisodicError):
        langmem_summarize(("hello",), max_chars=0)
