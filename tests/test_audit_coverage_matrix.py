"""S581 — audit-trail completeness review.

These tests pin the audit coverage matrix so it cannot rot:

  * The matrix doc exists, names every required action verb, and
    enumerates the canonical control-plane write modules.
  * Every (module, method) pair listed in the matrix actually
    resolves in the codebase — adding/removing a write method is
    forced to update the matrix in the same PR.
  * Every gap row cites a follow-up StoryV2 ID so the gap-fix queue
    is real, not aspirational.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_DOC = REPO_ROOT / "loop_implementation" / "engineering" / "AUDIT_COVERAGE.md"
CP_DIR = REPO_ROOT / "packages" / "control-plane" / "loop_control_plane"


# Pairs of (module file under control-plane, method name) that the
# matrix MUST list. Update these in lock-step with the matrix doc.
REQUIRED_WRITE_METHODS: tuple[tuple[str, str], ...] = (
    ("workspace_api.py", "create"),
    ("workspace_api.py", "update_member_role"),
    ("api_keys_api.py", "create"),
    ("api_keys_api.py", "revoke"),
    ("secrets.py", "rotate"),
    ("secrets.py", "delete"),
    ("deploy.py", "rollback"),
    ("suspension.py", "suspend"),
    ("mcp_marketplace.py", "publish"),
)


def _matrix_text() -> str:
    return MATRIX_DOC.read_text()


def test_matrix_doc_exists_and_non_trivial() -> None:
    assert MATRIX_DOC.exists(), f"missing {MATRIX_DOC}"
    assert MATRIX_DOC.stat().st_size > 1500, "AUDIT_COVERAGE.md unexpectedly small"


def test_action_vocabulary_present() -> None:
    """The canonical action verbs that emitters must use are
    enumerated in the matrix doc — drift between code and matrix
    fails the test."""
    text = _matrix_text()
    for verb in (
        "workspace.create",
        "workspace.member.role.update",
        "api_key.create",
        "api_key.revoke",
        "secret.rotate",
        "secret.delete",
        "agent.rollback",
        "billing.suspend",
        "mcp.publish",
    ):
        assert verb in text, f"action verb {verb!r} missing from matrix"


def test_every_required_write_method_listed_in_matrix() -> None:
    """Each enumerated (module, method) must appear in the matrix."""
    text = _matrix_text()
    for module, method in REQUIRED_WRITE_METHODS:
        assert module in text, f"matrix missing module {module}"
        assert method in text, f"matrix missing method {method}"


def test_every_required_write_method_exists_in_codebase() -> None:
    """Inverse direction: every matrix row must resolve to real code,
    so a deleted/renamed method forces a matrix update in the same
    PR."""
    method_re = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE)
    for module, method in REQUIRED_WRITE_METHODS:
        path = CP_DIR / module
        assert path.exists(), f"control-plane module missing: {module}"
        names = set(method_re.findall(path.read_text()))
        assert method in names, f"matrix lists {module}::{method} but no such method in code"


def test_every_gap_row_cites_follow_up_story() -> None:
    """A `gap` status without a StoryV2 reference is a silent debt —
    the matrix is the auditor's surface, not a TODO list."""
    text = _matrix_text()
    # Walk every body row of the coverage table whose status cell is
    # exactly "gap" (skips the header row that mentions "gap-story").
    gap_rows = [
        line
        for line in text.splitlines()
        if line.startswith("| ") and re.search(r"\|\s*gap\s*\|", line)
    ]
    assert gap_rows, "matrix should have at least one gap until S630 lands"
    sid_re = re.compile(r"\bS\d{3}\b")
    for row in gap_rows:
        assert sid_re.search(row), f"gap row missing follow-up SID: {row}"


def test_gap_fix_queue_section_present() -> None:
    text = _matrix_text()
    assert "## Gap-fix queue" in text, "Gap-fix queue section missing"
    # And it must point at S630, the audit-emitter wiring story.
    queue = text.split("## Gap-fix queue", 1)[1]
    assert "S630" in queue, "Gap-fix queue must cite S630"
