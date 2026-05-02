"""Tests for the continuous fuzz harness (S800)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "tools" / "fuzz_harness.py"
ISSUE_FILER = REPO / "tools" / "fuzz_report_to_issue.py"
WORKFLOW = REPO / ".github" / "workflows" / "fuzz-nightly.yml"


def test_harness_runs_with_zero_crashes(tmp_path: Path) -> None:
    """Smoke test: 50 iters per campaign, no unexpected crashes."""
    out = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--iterations",
            "50",
            "--seed",
            "0xC0FFEE",
            "--out",
            str(out),
            "--fail-on-crash",
        ],
        check=True,
        cwd=REPO,
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["totals"]["crashes"] == 0
    assert report["totals"]["iterations"] >= 200  # 4 campaigns × 50
    # At least one expected-exception path was exercised (oracle is wired).
    assert report["totals"]["expected_raises"] > 0
    names = {c["name"] for c in report["campaigns"]}
    # All four high-risk surfaces are covered.
    assert "cp-api/paseto.decode_local" in names
    assert "cp-api/audit_export.export_audit_csv" in names
    assert "cp-api/audit_events.hash_payload" in names
    assert "cp-api/byo_vault.VaultConfig" in names


def test_issue_filer_dry_run(tmp_path: Path) -> None:
    """The issue filer collapses duplicate signatures and respects dry-run."""
    fake = tmp_path / "report.json"
    fake.write_text(
        json.dumps(
            {
                "seed": 1,
                "campaigns": [
                    {
                        "name": "demo",
                        "iterations": 2,
                        "duration_s": 0.0,
                        "expected_raises": 0,
                        "crashes": [
                            {
                                "iteration": 0,
                                "kind": "AssertionError",
                                "trace": 'File "x.py", line 1, in foo\nAssertionError',
                            },
                            {
                                "iteration": 1,
                                "kind": "AssertionError",
                                "trace": 'File "x.py", line 1, in foo\nAssertionError',
                            },
                        ],
                    }
                ],
                "totals": {"iterations": 2, "expected_raises": 0, "crashes": 2},
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ISSUE_FILER),
            "--report",
            str(fake),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    # Two crashes share a signature — only one issue gets filed.
    assert "filed 1 fuzz issue(s); 1 unique signatures" in proc.stdout


def test_nightly_workflow_shape() -> None:
    """The workflow runs nightly, has issue-write perms, and uploads a report."""
    raw = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(raw)
    triggers = workflow.get("on") or workflow.get(True)
    assert triggers is not None
    assert "schedule" in triggers
    crons = [item.get("cron") for item in triggers["schedule"]]
    assert any(c and "* * *" in c for c in crons), "expected a daily cron"
    assert "workflow_dispatch" in triggers
    perms = workflow["permissions"]
    assert perms.get("issues") == "write"
    job = workflow["jobs"]["fuzz"]
    step_names = [s.get("name", "") for s in job["steps"]]
    assert any("Run fuzz campaigns" in n for n in step_names)
    assert any("File issues for crashes" in n for n in step_names)
    assert any("Upload fuzz report" in n for n in step_names)
    assert any("Fail run on crashes" in n for n in step_names)
    assert "fuzz-report.json" in raw
