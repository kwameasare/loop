"""Contract tests for `.github/workflows/release.yml`.

The release workflow used to reference `packages/runtime/Dockerfile`, a
path that doesn't exist (P0.6d in the prod-readiness audit). The first
tagged release would have failed at docker-build. This file pins the
shape of release.yml so it can't drift back into a broken state:

* every `file:` reference to a Dockerfile must point at an actual file
  in the tree;
* every job that pushes to PyPI must declare an `environment:` so a
  reviewer-approval gate can be enforced (P1 from the audit);
* signed images go through cosign with `--certificate-identity-regexp`
  set to the release workflow path on tag refs.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def _release_yaml() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _all_steps(workflow: dict[str, object]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    jobs = workflow.get("jobs", {})
    assert isinstance(jobs, dict)
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if isinstance(steps, list):
            out.extend(s for s in steps if isinstance(s, dict))
    return out


def test_every_dockerfile_reference_exists() -> None:
    """Regression: `packages/runtime/Dockerfile` does not exist; the
    actual Dockerfiles are at `packages/control-plane/Dockerfile` and
    `packages/data-plane/Dockerfile`. Any future drift would silently
    re-break tagged releases."""
    workflow = _release_yaml()
    seen: list[str] = []
    for step in _all_steps(workflow):
        with_block = step.get("with", {})
        if not isinstance(with_block, dict):
            continue
        file_ref = with_block.get("file")
        if isinstance(file_ref, str) and file_ref.endswith("Dockerfile"):
            seen.append(file_ref)
            assert (ROOT / file_ref).is_file(), f"release.yml references missing {file_ref}"
    # Belt-and-suspenders: the release flow must build at least one image,
    # and that image must be cp-api or dp-runtime (the two real ones).
    assert seen, "release.yml builds no docker images"
    assert any("control-plane" in f or "data-plane" in f for f in seen), seen


def test_pypi_publish_job_has_environment_gate() -> None:
    """Regression: `pypa/gh-action-pypi-publish` on tag push without
    an `environment:` declaration means a misfired tag publishes
    globally with no human-in-the-loop. P1 from the audit."""
    workflow = _release_yaml()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    publishing_jobs = [
        (name, job)
        for name, job in jobs.items()
        if isinstance(job, dict)
        and any(
            isinstance(s, dict) and "pypi-publish" in str(s.get("uses", ""))
            for s in job.get("steps", [])
            if isinstance(s, dict)
        )
    ]
    assert publishing_jobs, "no PyPI publishing job found in release.yml"
    for name, job in publishing_jobs:
        env = job.get("environment")
        assert env, f"job {name!r} publishes to PyPI but has no `environment:` gate"


def test_image_jobs_use_cosign_with_release_workflow_identity() -> None:
    """Tag-release images must be cosign-signed with the release.yml
    workflow identity so verification scripts can distinguish them
    from main-branch builds."""
    workflow = _release_yaml()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    image_jobs = [
        (name, job)
        for name, job in jobs.items()
        if isinstance(job, dict)
        and any(
            isinstance(s, dict)
            and "build-push-action" in str(s.get("uses", ""))
            for s in job.get("steps", [])
            if isinstance(s, dict)
        )
    ]
    assert image_jobs, "no docker-build jobs in release.yml"
    for name, job in image_jobs:
        env_block = job.get("env", {}) if isinstance(job.get("env"), dict) else {}
        regexp = env_block.get("COSIGN_CERT_IDENTITY_REGEXP", "")
        assert "release.yml" in str(regexp), (
            f"job {name!r}: COSIGN_CERT_IDENTITY_REGEXP must scope to release.yml"
        )
        assert "refs/tags" in str(regexp), (
            f"job {name!r}: COSIGN_CERT_IDENTITY_REGEXP must scope to tag refs"
        )
        steps = job.get("steps", [])
        joined = "\n".join(str(s.get("run", "")) for s in steps if isinstance(s, dict))
        assert "cosign sign" in joined, f"job {name!r} missing cosign sign step"
        assert "cosign verify" in joined, f"job {name!r} missing cosign verify step"
