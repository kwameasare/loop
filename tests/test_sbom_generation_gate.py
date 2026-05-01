"""S578 — SBOM generation in CI (CycloneDX).

The required `security` workflow job runs `anchore/sbom-action` on every
PR and on every push to main, producing a CycloneDX 1.5 JSON SBOM
covering the workspace (Python via uv.lock, Node via pnpm-lock.yaml).
The artifact is uploaded so the SOC2 evidence collector (S571) can pull
it from each green run.

These tests pin the wiring so a future refactor of ci.yml does not
silently drop the SBOM step.
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


def _sbom_step(job: dict) -> dict:
    for step in job["steps"]:
        if step.get("name", "").lower().startswith("generate sbom"):
            return step
    raise AssertionError("Generate SBOM step missing from security job")


def test_security_job_includes_sbom_step_pinned() -> None:
    """The SBOM step must exist and be pinned to a versioned anchore action."""
    step = _sbom_step(_load_security_job())
    uses = step.get("uses", "")
    assert uses.startswith("anchore/sbom-action@"), f"unexpected action: {uses!r}"
    # Version must be present (e.g. @v0.17.7), not a floating ref.
    assert "@v" in uses, f"sbom-action must be pinned to a version tag, got {uses!r}"


def test_sbom_step_produces_cyclonedx_json_artifact() -> None:
    step = _sbom_step(_load_security_job())
    with_block = step.get("with", {})
    assert with_block.get("format") == "cyclonedx-json", (
        f"SBOM format must be cyclonedx-json, got {with_block.get('format')!r}"
    )
    output = with_block.get("output-file", "")
    assert output.endswith(".cdx.json"), (
        f"SBOM output file must use .cdx.json suffix (CycloneDX convention), got {output!r}"
    )
    # Artifact must be uploaded so the evidence collector can fetch it.
    assert with_block.get("upload-artifact") is True, "SBOM artifact must be uploaded"
    artifact_name = with_block.get("artifact-name", "")
    assert artifact_name, "SBOM artifact must have an explicit name"


def test_sbom_step_runs_after_secrets_gate() -> None:
    """SBOM generation should be the last security step so a failing
    gitleaks/trivy scan short-circuits the job before we waste compute
    generating an SBOM that we would discard anyway."""
    job = _load_security_job()
    step_names = [s.get("name", "") for s in job["steps"]]
    secrets_idx = next(
        (
            i
            for i, n in enumerate(step_names)
            if "gitleaks" in n.lower() or "secrets scan" in n.lower()
        ),
        -1,
    )
    sbom_idx = next(
        (i for i, n in enumerate(step_names) if n.lower().startswith("generate sbom")),
        -1,
    )
    assert secrets_idx >= 0 and sbom_idx >= 0
    assert sbom_idx > secrets_idx, (
        f"SBOM step must run after the gitleaks step (secrets at {secrets_idx}, sbom at {sbom_idx})"
    )


def test_security_job_remains_required_and_unconditional() -> None:
    """Branch protection requires the security job to run on every PR;
    adding an `if:` would silently make it skippable."""
    job = _load_security_job()
    assert "if" not in job, "security job must remain unconditional (no `if:` key)"
    assert job.get("runs-on") == "ubuntu-latest"
