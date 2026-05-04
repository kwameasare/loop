"""Checks for Bitnami subchart mirroring workflow and operator guide."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "mirror-bitnami-subcharts.yml"
HOWTO = ROOT / "loop_implementation" / "engineering" / "HOWTO_BITNAMI_MIRROR.md"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_mirror_workflow_runs_weekly_and_manually() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))

    assert "workflow_dispatch" in triggers
    assert {"cron": "11 3 * * 1"} in triggers["schedule"]


def test_mirror_workflow_pushes_charts_and_images_to_ghcr() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["mirror-bitnami-subcharts"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert "postgresql:15.5.38" in runs
    assert "redis:20.3.0" in runs
    assert "minio:14.10.5" in runs
    assert "clickhouse:6.2.18" in runs
    assert "helm chart save" in runs
    assert "helm chart push" in runs
    assert "crane copy" in runs
    assert "ghcr.io/loop-ai/mirrored/bitnami/charts" in runs
    assert "ghcr.io/loop-ai/mirrored/bitnami/" in runs


def test_howto_documents_rotation_steps() -> None:
    text = HOWTO.read_text()

    assert "mirror-bitnami-subcharts.yml" in text
    assert "infra/helm/loop/Chart.yaml" in text
    assert "helm dependency build infra/helm/loop" in text
    assert "workflow_dispatch" in text
