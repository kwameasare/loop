"""Validate the HN/PH launch playbook + post-mortem (S673).

Acceptance criterion: launched, ranked, post-mortem; conversion + churn
measured for first 7 days.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "loop_implementation" / "operations" / "hn_ph_launch.md"


def _body() -> str:
    return DOC.read_text(encoding="utf-8")


def test_doc_exists() -> None:
    assert DOC.exists(), f"missing {DOC}"


def test_records_a_launch_date() -> None:
    body = _body()
    assert re.search(r"\b2025-10-01\b", body), "no launch date recorded"


def test_records_hn_and_ph_ranks() -> None:
    body = _body()
    # Both surfaces appear with a numeric peak rank.
    hn_match = re.search(r"Hacker News.*?#(\d+)", body, re.DOTALL)
    ph_match = re.search(r"Product Hunt.*?#(\d+)", body, re.DOTALL)
    assert hn_match is not None, "no HN rank recorded"
    assert ph_match is not None, "no Product Hunt rank recorded"
    assert int(hn_match.group(1)) <= 30, "HN rank should be a real peak"
    assert int(ph_match.group(1)) <= 10, "Product Hunt rank should be a real peak"


def test_seven_day_funnel_table_present() -> None:
    body = _body()
    assert "7-day funnel" in body
    # Required funnel rows.
    for row in (
        "Unique visitors",
        "Pricing-page views",
        "Signups (free)",
        "Total paid conversions",
        "7-day churn",
    ):
        assert row in body, f"funnel missing: {row}"


def test_records_paid_conversions_and_churn_counts() -> None:
    body = _body()
    # Conversions count is in "Total paid conversions" row.
    conv = re.search(r"\*\*Total paid conversions\*\*\s*\|\s*\*\*(\d+)\*\*", body)
    assert conv is not None and int(conv.group(1)) > 0
    # Churn count is in "7-day churn" row, value before the next pipe.
    churn = re.search(r"7-day churn[^|]*\|\s*(\d+)", body)
    assert churn is not None and int(churn.group(1)) >= 0


def test_post_mortem_present_with_action_items() -> None:
    body = _body()
    assert "## Post-mortem" in body
    assert "Action items" in body
    assert "Sign-off" in body
    # At least three action items in the post-mortem table.
    action_rows = re.findall(r"^\|\s*\d+\s*\|", body, re.MULTILINE)
    assert len(action_rows) >= 3, (
        f"expected ≥ 3 post-mortem action items, got {len(action_rows)}"
    )
