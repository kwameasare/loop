"""Pin SOC2 Type 1 kickoff doc structure (S582).

The kickoff artifact (`engineering/SOC2_TYPE1_KICKOFF.md`) commits
Loop's engineering org to a specific Type 1 audit window and an
evidence pack scope. These tests gate that commitment by making sure
the doc cannot silently drift away from the things it claims:

- the audit framing table is present with all required fields,
- the engineering-managed evidence rows reference real repo paths
  that resolve in this checkout,
- the engineering pre-kickoff prerequisite list cites real story IDs
  that exist in the StoryV2 backlog,
- cross-link from `SOC2.md` is live (the doc is discoverable from the
  auditor's entry point).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KICKOFF = REPO_ROOT / "loop_implementation" / "engineering" / "SOC2_TYPE1_KICKOFF.md"
SOC2 = REPO_ROOT / "loop_implementation" / "engineering" / "SOC2.md"
STORIES = REPO_ROOT / "tools" / "_stories_v2.py"


def _kickoff_text() -> str:
    return KICKOFF.read_text(encoding="utf-8")


def test_kickoff_doc_exists_and_nontrivial() -> None:
    assert KICKOFF.exists(), "SOC2_TYPE1_KICKOFF.md is missing"
    assert KICKOFF.stat().st_size > 2500, "kickoff doc is suspiciously small"


def test_audit_framing_table_complete() -> None:
    text = _kickoff_text()
    for required in (
        "Framework",
        "Trust criteria",
        "Snapshot date",
        "Fieldwork window",
        "Report target",
        "Scope — services",
        "Scope — environments",
        "Out of scope",
    ):
        assert required in text, f"audit framing table missing row: {required!r}"


def test_snapshot_date_committed() -> None:
    """Window dates committed (S582 AC) — must be ISO-format and not TBD."""
    text = _kickoff_text()
    # Find the Snapshot date row and assert it has a real ISO date.
    match = re.search(r"\|\s*Snapshot date\s*\|\s*\*?\*?(\d{4}-\d{2}-\d{2})", text)
    assert match is not None, "Snapshot date is not a committed YYYY-MM-DD value"
    assert "TBD" not in text.split("## Audit framing")[1].split("## ")[0], (
        "audit framing block still contains TBD — window must be committed"
    )


def test_evidence_pack_engineering_rows_reference_real_files() -> None:
    """Every repo-path-shaped reference in the engineering evidence
    section must resolve in this checkout. Drift forces a doc update
    in the same PR that moves/renames the file."""
    text = _kickoff_text()
    # Slice between the engineering evidence header and the next
    # operations-evidence header so we only audit our own claims.
    eng_block = text.split("### Engineering-managed evidence")[1].split(
        "### Operations-managed evidence"
    )[0]
    # Pick out backtick-quoted paths that look like repo paths
    # (contain a slash and a file extension).
    paths = re.findall(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`", eng_block)
    assert paths, "no repo paths cited in engineering evidence section"
    missing = [p for p in paths if not (REPO_ROOT / p).exists()]
    assert not missing, f"evidence paths do not resolve: {missing}"


def test_pre_kickoff_prereqs_cite_real_story_ids() -> None:
    """The 'Pre-kickoff prerequisites' checklist names story IDs
    (e.g. S571). Those IDs must exist in the StoryV2 source so the
    auditor's evidence pack is wired to actual tracker rows."""
    text = _kickoff_text()
    prereq_block = text.split("## Pre-kickoff prerequisites")[1].split("## ")[0]
    cited = set(re.findall(r"\bS\d{3}\b", prereq_block))
    assert cited, "no StoryV2 IDs cited in prerequisites"
    stories_text = STORIES.read_text(encoding="utf-8")
    missing = [sid for sid in cited if f'"{sid}"' not in stories_text]
    assert not missing, f"prereq IDs not in _stories_v2.py: {missing}"


def test_soc2_doc_cross_links_kickoff() -> None:
    """The auditor's primary entry point is SOC2.md. The kickoff doc
    must be linked from it so the evidence pack is discoverable."""
    assert SOC2.exists()
    assert "SOC2_TYPE1_KICKOFF" in SOC2.read_text(encoding="utf-8"), (
        "SOC2.md must cross-link SOC2_TYPE1_KICKOFF.md so the auditor "
        "can find the kickoff artifact from the control map"
    )
