"""Checks for CI license compliance and blocking audit policy wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(CI_WORKFLOW.read_text()))


def test_ci_has_required_license_compliance_job() -> None:
    workflow = _workflow()
    jobs = cast(dict[str, Any], workflow["jobs"])

    assert "license-compliance" in jobs
    job = cast(dict[str, Any], jobs["license-compliance"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert any(
        str(step.get("uses", "")).startswith("anchore/sbom-action@")
        for step in cast(list[dict[str, Any]], job["steps"])
    )
    assert "tools/license_check.py" in runs
    assert "tools/license_allowlist.json" in runs


def test_security_job_blocks_on_pip_and_npm_audits() -> None:
    workflow = _workflow()
    security = cast(dict[str, Any], workflow["jobs"]["security"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], security["steps"]))

    assert "check_audit_allowlist_expiry.py" in runs
    assert "pip-audit --format json" in runs
    assert "npm audit --prefix apps/studio --audit-level=high --json" in runs
    assert "pip_audit_allow.txt" in runs
    assert "tools/npm_audit_allow.json" in runs
