"""S571 — SOC2 control mapping (CC1-CC9) → evidence sources doc.

The doc at `loop_implementation/engineering/SOC2.md` carries the
canonical mapping from each Trust Services Criterion control to the
concrete evidence source the auditor (and Vanta) will pull. These
tests make the structure load-bearing so a future edit cannot
silently delete a control family or unwire the evidence index.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOC2_DOC = REPO_ROOT / "loop_implementation" / "engineering" / "SOC2.md"


def _read() -> str:
    return SOC2_DOC.read_text()


def test_soc2_doc_present_and_non_empty() -> None:
    assert SOC2_DOC.exists(), f"missing {SOC2_DOC}"
    assert SOC2_DOC.stat().st_size > 1000, "SOC2.md unexpectedly small"


def test_all_cc_families_present() -> None:
    """CC1 through CC9 must all have a level-3 heading."""
    text = _read()
    for n in range(1, 10):
        pattern = rf"###\s+CC{n}\b"
        assert re.search(pattern, text), f"CC{n} family heading missing from SOC2.md"


def test_evidence_sources_index_section_present() -> None:
    """The doc must carry the Evidence sources index — that is the
    deliverable of S571."""
    text = _read()
    assert "## Evidence sources index" in text, "Evidence sources index section missing — see S571"


def test_evidence_index_references_known_ci_gates() -> None:
    """Each CI security gate we have shipped must appear in the
    evidence index so the auditor knows where to pull from."""
    text = _read()
    # Anchor the search to the Evidence sources index section so a
    # passing match elsewhere in the doc does not satisfy the test.
    section = text.split("## Evidence sources index", 1)[1].split("## Control families", 1)[0]
    for needle in (
        "trivy",  # S579 fs scan
        "snyk",  # S579 SCA
        "gitleaks",  # S580 secrets
        "CycloneDX",  # S578 SBOM
        "S578",
        "S579",
        "S580",
    ):
        assert needle in section, f"Evidence sources index missing reference to {needle!r}"


def test_cc71_marked_done_with_concrete_evidence() -> None:
    """CC7.1 (vulnerability scanning on every PR) is now fully covered
    by the trivy + snyk + gitleaks + SBOM stack. The status column
    must reflect that and the evidence column must point at the
    workflow file."""
    text = _read()
    # Find the CC7.1 control-table row (not the evidence-index row,
    # which lists CC7.1 in its "controls satisfied" cell). The control
    # table row begins with `| CC7.1 |`.
    cc71_rows = [line for line in text.splitlines() if line.startswith("| CC7.1 |")]
    assert cc71_rows, "CC7.1 control row missing"
    row = cc71_rows[0]
    assert "ci.yml" in row, "CC7.1 evidence must point at ci.yml"
    assert "done" in row.lower(), "CC7.1 should be marked done now that the gates ship"


def test_change_log_records_s571() -> None:
    text = _read()
    log = text.split("## Change log", 1)[1] if "## Change log" in text else ""
    assert "S571" in log, "Change log must record the S571 update"
    assert "copilot-titan" in log, "Change log must record the author"
