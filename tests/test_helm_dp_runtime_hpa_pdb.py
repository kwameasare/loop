"""Smoke tests for dp-runtime HPA + PDB templates added in S442.

Mirrors tests/test_helm_cp_api_hpa_pdb.py for the runtime component.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
HPA = CHART / "templates" / "runtime-hpa.yaml"
PDB = CHART / "templates" / "runtime-pdb.yaml"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def test_runtime_hpa_template_targets_runtime_deployment() -> None:
    text = HPA.read_text()
    assert "apiVersion: autoscaling/v2" in text
    assert "kind: HorizontalPodAutoscaler" in text
    assert ".Values.runtime.enabled" in text
    assert ".Values.runtime.autoscaling.enabled" in text
    assert "loop.fullname" in text
    assert "-runtime" in text
    assert "kind: Deployment" in text


def test_runtime_pdb_template_uses_xor_min_max() -> None:
    text = PDB.read_text()
    assert "apiVersion: policy/v1" in text
    assert "kind: PodDisruptionBudget" in text
    assert ".Values.runtime.pdb.enabled" in text
    assert "minAvailable" in text and "maxUnavailable" in text
    assert "{{- else if" in text
    assert "app.kubernetes.io/component: runtime" in text


def test_runtime_values_have_autoscaling_and_pdb_blocks() -> None:
    values = cast(dict[str, dict[str, object]], yaml.safe_load(VALUES.read_text()))
    rt = values["runtime"]
    auto = cast(dict[str, object], rt["autoscaling"])
    assert auto["enabled"] is False
    assert auto["minReplicas"] == 3
    assert auto["maxReplicas"] == 30
    assert auto["targetCPUUtilizationPercentage"] == 70
    pdb = cast(dict[str, object], rt["pdb"])
    assert pdb["enabled"] is True
    assert pdb["minAvailable"] == 2


def test_runtime_schema_rejects_missing_max_replicas() -> None:
    schema = json.loads(SCHEMA.read_text())
    bad = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    rt = cast(dict[str, object], bad["runtime"])
    auto = cast(dict[str, object], dict(rt["autoscaling"]))  # type: ignore[arg-type]
    del auto["maxReplicas"]
    rt["autoscaling"] = auto
    try:
        jsonschema.validate(bad, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema should reject autoscaling without maxReplicas")
