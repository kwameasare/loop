from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "packages" / "control-plane" / "Dockerfile"
DP_DOCKERFILE = ROOT / "packages" / "data-plane" / "Dockerfile"
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


def _signature_policy_errors(job: dict[str, Any], image_env: str, main_env: str) -> list[str]:
    text = yaml.safe_dump(job)
    run_text = "\n".join(str(step.get("run", "")) for step in _steps(job))
    errors: list[str] = []
    if job.get("permissions", {}).get("id-token") != "write":
        errors.append("workflow must grant OIDC id-token for keyless signing")
    if "sigstore/cosign-installer" not in text:
        errors.append("workflow must install cosign")
    if "imjasonh/setup-crane" not in text or "crane digest" not in run_text:
        errors.append("workflow must resolve pushed image digests")
    if f"docker push \"${image_env}\"" not in run_text or f"docker push \"${main_env}\"" not in run_text:
        errors.append("workflow must push both sha and main tags")
    if 'test "$main_digest" = "$digest"' not in run_text:
        errors.append("workflow must prove main tag matches signed digest")
    if "cosign sign --yes" not in run_text:
        errors.append("workflow must sign the immutable digest")
    if (
        "cosign verify" not in run_text
        or "--certificate-identity-regexp" not in run_text
        or "--certificate-oidc-issuer" not in run_text
    ):
        errors.append("workflow must verify the cosign certificate identity")
    return errors


def test_cp_api_dockerfile_is_distroless_nonroot() -> None:
    dockerfile = DOCKERFILE.read_text()

    assert "FROM python:3.12-slim-bookworm AS builder" in dockerfile
    assert "COPY --from=builder /opt/venv /opt/venv" in dockerfile
    assert _dockerfile_policy_errors(dockerfile) == []


def test_service_dockerfiles_install_local_channel_core_dependency() -> None:
    """The local loop-channels-core package must be installed before
    loop-control-plane, otherwise image builds try to resolve it from PyPI."""
    for dockerfile_path in (DOCKERFILE, DP_DOCKERFILE):
        dockerfile = dockerfile_path.read_text()
        assert "COPY packages/channels/core/pyproject.toml" in dockerfile
        assert "COPY packages/channels/core/loop_channels_core" in dockerfile
        assert "./packages/channels/core" in dockerfile


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


def test_service_image_workflows_sign_and_verify_pushed_digests() -> None:
    jobs = _workflow_jobs()

    assert _signature_policy_errors(
        cast(dict[str, Any], jobs["cp-api-image"]),
        "CP_API_IMAGE",
        "CP_API_IMAGE_MAIN",
    ) == []
    assert _signature_policy_errors(
        cast(dict[str, Any], jobs["dp-runtime-image"]),
        "DP_RUNTIME_IMAGE",
        "DP_RUNTIME_IMAGE_MAIN",
    ) == []


def test_cp_api_image_workflow_policy_rejects_missing_scan_and_push() -> None:
    bad_job: dict[str, Any] = {
        "env": {"CP_API_MAX_BYTES": "120000000"},
        "steps": [{"uses": "docker/build-push-action@v6"}],
    }

    assert _workflow_policy_errors(bad_job) == [
        "workflow must scan HIGH/CRITICAL vulnerabilities",
        "workflow must push to GHCR on main",
    ]


def test_image_signature_policy_rejects_unsigned_push() -> None:
    bad_job: dict[str, Any] = {
        "permissions": {"contents": "read", "packages": "write"},
        "steps": [
            {"uses": "actions/checkout@v4"},
            {"run": 'docker push "$IMAGE"\ndocker push "$IMAGE_MAIN"'},
        ],
    }

    assert _signature_policy_errors(bad_job, "IMAGE", "IMAGE_MAIN") == [
        "workflow must grant OIDC id-token for keyless signing",
        "workflow must install cosign",
        "workflow must resolve pushed image digests",
        "workflow must prove main tag matches signed digest",
        "workflow must sign the immutable digest",
        "workflow must verify the cosign certificate identity",
    ]


def test_cp_api_image_check_is_required_for_main() -> None:
    assert "- `CI / cp-api-image`" in BRANCH_PROTECTION.read_text()
