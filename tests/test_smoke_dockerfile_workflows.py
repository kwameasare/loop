"""Regression checks for shared smoke Dockerfile workflow usage (S19 hardening)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_DOCKERFILE = ROOT / "scripts" / "Dockerfile.smoke"
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "helm-e2e.yml",
    ROOT / ".github" / "workflows" / "cross-cloud-smoke.yml",
    ROOT / ".github" / "workflows" / "eu-smoke.yml",
    ROOT / ".github" / "workflows" / "turn-latency-k6.yml",
    ROOT / ".github" / "workflows" / "runtime-sse-1000.yml",
)


def test_shared_smoke_dockerfile_exists_with_configurable_args() -> None:
    text = SHARED_DOCKERFILE.read_text()

    assert "ARG SMOKE_SCRIPT" in text
    assert "ARG SMOKE_PORTS" in text
    assert "COPY ${SMOKE_SCRIPT} /server.py" in text
    assert "ENV HELM_SMOKE_PORTS=${SMOKE_PORTS}" in text
    assert "ENV LOOP_OPENAI_FIXTURE_PORT=${SMOKE_PORTS}" in text


def test_workflows_use_shared_smoke_dockerfile_instead_of_heredocs() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text()
        assert "scripts/Dockerfile.smoke" in text, f"{workflow} must use shared Dockerfile"
        assert "cat > /tmp/loop-helm-smoke.Dockerfile" not in text
        assert "cat > /tmp/loop-openai-sse-fixture.Dockerfile" not in text
