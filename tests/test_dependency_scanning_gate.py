"""S579 — dependency-scanning gate (trivy + snyk).

The required `security` workflow job runs both `aquasecurity/trivy-action`
(filesystem scan, blocking on HIGH/CRITICAL OS+library findings) and
`snyk/actions/python` (SCA, blocking on HIGH+) on every PR and on every
push to main. Snyk is gated on the SNYK_TOKEN secret being present so
the gate is off in fork PRs / cold-clone CI where the token is not
available, but is a hard gate in production CI.

These tests pin the wiring so a future refactor of ci.yml does not
silently drop either scanner.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load_security_job() -> dict:
    data = yaml.safe_load(CI_WORKFLOW.read_text())
    assert "security" in data["jobs"], "security job missing from ci.yml"
    return data["jobs"]["security"]


def _step_by_name(job: dict, needle: str) -> dict:
    for step in job["steps"]:
        if needle.lower() in step.get("name", "").lower():
            return step
    raise AssertionError(f"step containing {needle!r} missing from security job")


def test_security_job_includes_trivy_blocking_fs_scan() -> None:
    step = _step_by_name(_load_security_job(), "trivy")
    uses = step.get("uses", "")
    assert uses.startswith("aquasecurity/trivy-action@"), f"unexpected action: {uses!r}"
    with_block = step.get("with", {})
    assert with_block.get("scan-type") == "fs"
    sev = with_block.get("severity", "")
    assert "CRITICAL" in sev and "HIGH" in sev, f"trivy must block on HIGH+CRITICAL, got {sev!r}"
    # Must be a hard gate.
    assert str(with_block.get("exit-code", "")) == "1", "trivy must fail the job on findings"


def test_security_job_includes_snyk_pinned() -> None:
    step = _step_by_name(_load_security_job(), "snyk")
    uses = step.get("uses", "")
    assert uses.startswith("snyk/actions/python@"), f"unexpected action: {uses!r}"
    # Pinned to a version (not @master / @main).
    ref = uses.split("@", 1)[1]
    assert ref and ref not in {"master", "main"}, (
        f"snyk action must be pinned to a version, got {ref!r}"
    )


def test_snyk_step_is_high_or_above_blocking() -> None:
    step = _step_by_name(_load_security_job(), "snyk")
    args = step.get("with", {}).get("args", "")
    assert "--severity-threshold=high" in args, (
        f"snyk must block at HIGH or higher to satisfy SOC2 dependency policy, got {args!r}"
    )


def test_snyk_step_uses_token_secret_and_is_token_gated() -> None:
    """Snyk requires SNYK_TOKEN. Step must read it from the repo secret
    (not committed) and must skip cleanly when the token is unset
    (fork PRs / cold-clone CI) — never silently succeed without scanning."""
    step = _step_by_name(_load_security_job(), "snyk")
    env = step.get("env", {})
    assert env.get("SNYK_TOKEN") == "${{ secrets.SNYK_TOKEN }}", (
        f"snyk must read SNYK_TOKEN from secrets, got {env!r}"
    )
    if_expr = step.get("if", "")
    assert "SNYK_TOKEN" in if_expr, (
        f"snyk step must be gated on SNYK_TOKEN presence so cold-clone CI does not "
        f"silently bypass the scan, got if={if_expr!r}"
    )


def test_security_job_remains_required_and_unconditional() -> None:
    job = _load_security_job()
    assert "if" not in job, "security job must remain unconditional"
    assert job.get("runs-on") == "ubuntu-latest"
