"""Workflow checks for Falco + loop-observability smoke validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "falco-observability-smoke.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_falco_smoke_workflow_triggers_on_relevant_paths() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))

    assert "pull_request" in triggers
    pr_paths = cast(list[str], triggers["pull_request"]["paths"])
    assert "infra/helm/loop-observability/**" in pr_paths
    assert "infra/falco/**" in pr_paths
    assert "infra/prometheus/**" in pr_paths


def test_falco_smoke_workflow_installs_obs_stack_and_asserts_alert() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["falco-observability-smoke"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert "helm dependency update infra/helm/loop-observability" in runs
    assert "helm upgrade --install loop-observability infra/helm/loop-observability" in runs
    assert "kubectl run falco-smoke" in runs
    assert "/api/v2/alerts" in runs
    assert "shell-spawned-in-pod" in runs
