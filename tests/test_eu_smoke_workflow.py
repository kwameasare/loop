"""Tests for the S597 EU-west nightly smoke workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "eu-smoke.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def _step_runs(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def test_eu_smoke_workflow_runs_nightly_and_manually() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["eu-smoke"])
    steps = cast(list[dict[str, Any]], job["steps"])
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    assert job["timeout-minutes"] == 14
    assert any(step.get("uses") == "helm/kind-action@v1.10.0" for step in steps)
    assert any(step.get("uses") == "azure/setup-helm@v4" for step in steps)
    assert "workflow_dispatch" in triggers
    assert triggers["schedule"][0]["cron"] == "31 4 * * *"


def test_eu_smoke_workflow_installs_eu_overlay_and_runs_smoke() -> None:
    job = cast(dict[str, Any], _workflow()["jobs"]["eu-smoke"])
    env = cast(dict[str, str], job["env"])
    runs = _step_runs(job)
    assert env["LOOP_NAMESPACE"] == "loop-eu-west"
    assert env["EU_SMOKE_REGION"] == "eu-west"
    assert "-f infra/helm/loop/values-eu-west.yaml" in runs
    assert '--namespace "$LOOP_NAMESPACE" --create-namespace' in runs
    assert "kind load docker-image loop/helm-smoke:ci --name loop-eu-smoke" in runs
    assert 'kubectl -n "$LOOP_NAMESPACE" port-forward svc/loop-loop-runtime 18081:8081' in runs
    assert "scripts/eu_smoke.sh" in runs
    assert 'kubectl -n "$LOOP_NAMESPACE" logs' in runs
