"""Tests for the STRIDE threat-model gate (S801)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import check_threat_model  # type: ignore[import-not-found]

GATE = REPO / "tools" / "check_threat_model.py"
DOC = REPO / "docs" / "THREAT_MODEL.md"
WORKFLOW = REPO / ".github" / "workflows" / "threat-model-gate.yml"


def _run(changed: list[str], *, pr_body: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), "--pr-body", pr_body],
        input="\n".join(changed) + "\n",
        capture_output=True,
        text=True,
        cwd=REPO,
    )


def test_passes_when_no_protected_paths_touched() -> None:
    proc = _run(["docs/index.md", "apps/studio/src/foo.tsx"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no protected paths touched" in proc.stdout


def test_fails_when_auth_changed_without_doc_update() -> None:
    proc = _run(["packages/control-plane/loop_control_plane/paseto.py"])
    assert proc.returncode == 2, proc.stdout
    assert "FAIL" in proc.stdout
    assert "paseto.py" in proc.stdout


def test_passes_when_auth_changed_with_threat_model_update() -> None:
    proc = _run(
        [
            "packages/control-plane/loop_control_plane/paseto.py",
            "docs/THREAT_MODEL.md",
        ]
    )
    assert proc.returncode == 0, proc.stdout
    assert "updated in this PR" in proc.stdout


def test_passes_with_skip_token_in_pr_body() -> None:
    proc = _run(
        ["packages/control-plane/loop_control_plane/saml_okta.py"],
        pr_body="Pure refactor — no auth-flow change.\n\nthreat-model: skip\n",
    )
    assert proc.returncode == 0, proc.stdout
    assert "logged bypass" in proc.stdout


def test_mutating_route_gate_fails_when_namespace_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        check_threat_model,
        "_audit_action_namespaces",
        lambda _: {"brand:new_namespace"},
    )

    code, log = check_threat_model.evaluate(
        changed=["packages/control-plane/loop_control_plane/_routes_workspaces.py"],
        mutating_route_files=["packages/control-plane/loop_control_plane/_routes_workspaces.py"],
    )

    assert code == 2
    assert any("missing STRIDE coverage for audit-action namespaces" in line for line in log)


def test_mutating_route_gate_passes_when_namespace_documented(monkeypatch) -> None:
    monkeypatch.setattr(
        check_threat_model,
        "_audit_action_namespaces",
        lambda _: {"workspace:member"},
    )

    code, log = check_threat_model.evaluate(
        changed=["packages/control-plane/loop_control_plane/_routes_workspaces.py"],
        mutating_route_files=["packages/control-plane/loop_control_plane/_routes_workspaces.py"],
    )

    assert code == 0
    assert any("required STRIDE coverage present" in line for line in log)


def test_detects_secrets_and_audit_paths() -> None:
    for path in (
        "packages/control-plane/loop_control_plane/byo_vault.py",
        "packages/control-plane/loop_control_plane/audit_events.py",
        "packages/control-plane/loop_control_plane/migrations/cp_0005_audit_events.py",
        "packages/control-plane/loop_control_plane/api_keys.py",
    ):
        proc = _run([path])
        assert proc.returncode == 2, f"expected gate to flag {path}; got {proc.stdout}"


def test_doc_lists_required_sections() -> None:
    text = DOC.read_text(encoding="utf-8")
    for section in (
        "STRIDE checklist",
        "STRIDE-protected paths",
        "Update log",
    ):
        assert section in text, f"docs/THREAT_MODEL.md missing section {section!r}"
    # The doc must enumerate all six STRIDE letters in the checklist.
    for letter in ("**S**", "**T**", "**R**", "**I**", "**D**", "**E**"):
        assert letter in text


def test_workflow_runs_on_pull_request_to_main() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True)
    assert "pull_request" in triggers
    assert "main" in triggers["pull_request"]["branches"]
    perms = workflow["permissions"]
    assert perms.get("pull-requests") == "read"
    job = workflow["jobs"]["threat-model"]
    cmds = " ".join(s.get("run", "") for s in job["steps"])
    assert "tools/check_threat_model.py" in cmds
    assert "gh pr diff" in cmds
    assert "--base" in cmds
    assert "--head" in cmds
