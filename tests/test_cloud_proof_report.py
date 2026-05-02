"""Tests for the S781 cloud portability proof report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cloud_proof_report.py"
REPORT = ROOT / "docs" / "CLOUD_PROOF.md"
WORKFLOW = ROOT / ".github" / "workflows" / "cross-cloud-smoke.yml"


def _run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cloud_proof_report_appends_green_and_red_marks(tmp_path: Path) -> None:
    report = tmp_path / "CLOUD_PROOF.md"
    report.write_text(
        "proof\n<!-- CLOUD_PROOF_HISTORY:BEGIN -->\n<!-- CLOUD_PROOF_HISTORY:END -->\n"
    )
    green = tmp_path / "cloud-proof-aws.json"
    red = tmp_path / "cloud-proof-gcp.json"

    assert (
        _run(
            "mark",
            "--cloud",
            "aws",
            "--region",
            "na-east",
            "--status",
            "success",
            "--run-url",
            "https://example.test/run/1",
            "--sha",
            "abcdef1234567890",
            "--output",
            str(green),
        ).returncode
        == 0
    )
    assert (
        _run(
            "mark",
            "--cloud",
            "gcp",
            "--region",
            "apac-sg",
            "--status",
            "failure",
            "--run-url",
            "https://example.test/run/2",
            "--sha",
            "999999999999abcd",
            "--output",
            str(red),
        ).returncode
        == 0
    )
    result = _run("append", "--report", str(report), str(green), str(red))

    text = report.read_text()
    assert result.returncode == 0, result.stderr
    assert "| `aws` | `na-east` | GREEN |" in text
    assert "| `gcp` | `apac-sg` | RED |" in text
    assert "`abcdef123456`" in text


def test_cloud_proof_report_rejects_unknown_status(tmp_path: Path) -> None:
    result = _run(
        "mark",
        "--cloud",
        "aws",
        "--region",
        "na-east",
        "--status",
        "maybe",
        "--run-url",
        "https://example.test/run/1",
        "--sha",
        "abc",
        "--output",
        str(tmp_path / "bad.json"),
    )

    assert result.returncode == 2
    assert "unsupported cloud proof status" in result.stderr


def test_cloud_proof_page_lists_capability_by_cloud_matrix() -> None:
    text = REPORT.read_text()
    for cloud in ("AWS", "Azure", "GCP", "Alibaba Cloud", "OVHcloud", "Hetzner", "Self-host"):
        assert cloud in text
    for capability in ("Kubernetes deploy", "Postgres", "Redis", "Object storage", "KMS"):
        assert f"| {capability} |" in text
    assert "<!-- CLOUD_PROOF_HISTORY:BEGIN -->" in text


def test_cross_cloud_workflow_publishes_nightly_proof_marks() -> None:
    data = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    publish = cast(dict[str, Any], data["jobs"]["publish-cloud-proof"])
    runs = "\n".join(str(step.get("run", "")) for step in publish["steps"])
    smoke_steps = cast(list[dict[str, Any]], data["jobs"]["cross-cloud-smoke"]["steps"])

    assert publish["needs"] == "cross-cloud-smoke"
    assert "schedule" in publish["if"]
    assert "workflow_dispatch" in publish["if"]
    assert "scripts/cloud_proof_report.py append" in runs
    assert "git push" in runs
    assert any(step.get("name") == "Upload cloud proof mark" for step in smoke_steps)
