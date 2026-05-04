"""Workflow checks for Helm chart validation and regional NOTES preflight."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "helm-chart-validation.yml"
OVERLAYS = (
    ROOT / "infra" / "helm" / "loop" / "values-eu-west.yaml",
    ROOT / "infra" / "helm" / "loop" / "values-us-east.yaml",
    ROOT / "infra" / "helm" / "loop" / "values-apac-sg.yaml",
)


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_helm_chart_validation_runs_on_helm_pr_changes() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))

    assert "pull_request" in triggers
    pr_paths = cast(list[str], triggers["pull_request"]["paths"])
    assert "infra/helm/**" in pr_paths
    assert "tools/check_helm_chart.py" in pr_paths


def test_helm_chart_validation_executes_structural_and_render_checks() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["helm-chart-validation"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert "tools/check_helm_chart.py" in runs
    assert "helm lint infra/helm/loop" in runs
    assert "helm template loop infra/helm/loop" in runs
    assert "values-eu-west.yaml values-us-east.yaml values-apac-sg.yaml" in runs
    assert "--set global.dataResidency=eu" in runs
    assert "regional preflight failed" in runs


def test_regional_overlays_exist_and_define_telemetry_endpoints() -> None:
    for overlay in OVERLAYS:
        text = overlay.read_text()
        assert "global:" in text
        assert "region:" in text
        assert "telemetry:" in text
        assert "metricsEndpoint:" in text
        assert "logsEndpoint:" in text
        assert "tracesEndpoint:" in text
