from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "packages" / "control-plane" / "Dockerfile"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
BRANCH_PROTECTION = ROOT / "docs" / "branch-protection.md"


def _workflow_jobs() -> dict[str, Any]:
    workflow = cast(dict[str, Any], yaml.safe_load(WORKFLOW.read_text()))
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    return cast(dict[str, Any], jobs)


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return cast(list[dict[str, Any]], steps)


def _final_stage(dockerfile: str) -> str:
    starts = [
        index
        for index, line in enumerate(dockerfile.splitlines())
        if line.upper().startswith("FROM ")
    ]
    assert starts
    return "\n".join(dockerfile.splitlines()[starts[-1] :])


def _dockerfile_policy_errors(dockerfile: str) -> list[str]:
    final_stage = _final_stage(dockerfile)
    errors: list[str] = []
    if "FROM gcr.io/distroless/cc-debian12:nonroot AS runtime" not in final_stage:
        errors.append("runtime stage must use distroless nonroot base")
    if "USER nonroot:nonroot" not in final_stage:
        errors.append("runtime stage must run as nonroot")
    if "apt-get" in final_stage or " apk " in final_stage:
        errors.append("runtime stage must not install packages")
    if 'ENTRYPOINT ["/opt/venv/bin/python"]' not in final_stage:
        errors.append("runtime entrypoint must exec Python without a shell")
    return errors


def _workflow_policy_errors(job: dict[str, Any]) -> list[str]:
    text = yaml.safe_dump(job)
    errors: list[str] = []
    if "docker/build-push-action" not in text:
        errors.append("workflow must build the image")
    if "CP_API_MAX_BYTES: '120000000'" not in text and 'CP_API_MAX_BYTES: "120000000"' not in text:
        errors.append("workflow must enforce the 120 MB budget")
    if "aquasecurity/trivy-action" not in text or "HIGH,CRITICAL" not in text:
        errors.append("workflow must scan HIGH/CRITICAL vulnerabilities")
    if "github.ref == 'refs/heads/main'" not in text or "docker push" not in text:
        errors.append("workflow must push to GHCR on main")
    return errors


def test_cp_api_dockerfile_is_distroless_nonroot() -> None:
    dockerfile = DOCKERFILE.read_text()

    assert "FROM python:3.12-slim-bookworm AS builder" in dockerfile
    assert "COPY --from=builder /opt/venv /opt/venv" in dockerfile
    assert _dockerfile_policy_errors(dockerfile) == []


def test_cp_api_dockerfile_policy_rejects_insecure_runtime() -> None:
    insecure = """
FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update
USER root
ENTRYPOINT python -m loop_control_plane.healthz
"""

    assert _dockerfile_policy_errors(insecure) == [
        "runtime stage must use distroless nonroot base",
        "runtime stage must run as nonroot",
        "runtime stage must not install packages",
        "runtime entrypoint must exec Python without a shell",
    ]


def test_cp_api_image_workflow_builds_scans_and_pushes_on_main() -> None:
    job = cast(dict[str, Any], _workflow_jobs()["cp-api-image"])
    steps = _steps(job)

    assert job["permissions"]["packages"] == "write"
    assert job["env"]["CP_API_IMAGE"].startswith("ghcr.io/loop-ai/cp-api:")
    assert _workflow_policy_errors(job) == []
    assert any(step.get("uses", "").startswith("docker/build-push-action@") for step in steps)
    assert any(step.get("uses", "").startswith("aquasecurity/trivy-action@") for step in steps)


def test_cp_api_image_workflow_policy_rejects_missing_scan_and_push() -> None:
    bad_job: dict[str, Any] = {
        "env": {"CP_API_MAX_BYTES": "120000000"},
        "steps": [{"uses": "docker/build-push-action@v6"}],
    }

    assert _workflow_policy_errors(bad_job) == [
        "workflow must scan HIGH/CRITICAL vulnerabilities",
        "workflow must push to GHCR on main",
    ]


def test_cp_api_image_check_is_required_for_main() -> None:
    assert "- `CI / cp-api-image`" in BRANCH_PROTECTION.read_text()
