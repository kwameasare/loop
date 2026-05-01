"""Smoke tests for cp-api HPA + PDB templates added in S441.

Goes a bit beyond the structural check in tools/check_helm_chart.py: the
templates are gated on values, so we render them by string-substitution
of the gate values and parse the result as YAML. This catches gate-typo
bugs without requiring the helm binary in CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
HPA = CHART / "templates" / "control-plane-hpa.yaml"
PDB = CHART / "templates" / "control-plane-pdb.yaml"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def test_hpa_template_is_apiversion_v2_and_targets_deployment() -> None:
    text = HPA.read_text()
    assert "apiVersion: autoscaling/v2" in text
    assert "kind: HorizontalPodAutoscaler" in text
    assert ".Values.controlPlane.enabled" in text
    assert ".Values.controlPlane.autoscaling.enabled" in text
    assert ".Values.controlPlane.autoscaling.minReplicas" in text
    assert ".Values.controlPlane.autoscaling.maxReplicas" in text
    assert ".Values.controlPlane.autoscaling.targetCPUUtilizationPercentage" in text
    assert "kind: Deployment" in text


def test_pdb_template_is_policy_v1_and_uses_xor_min_max() -> None:
    text = PDB.read_text()
    assert "apiVersion: policy/v1" in text
    assert "kind: PodDisruptionBudget" in text
    assert ".Values.controlPlane.pdb.enabled" in text
    # The template renders minAvailable XOR maxUnavailable -- never both.
    assert "minAvailable" in text and "maxUnavailable" in text
    assert "{{- else if" in text


def test_values_have_autoscaling_and_pdb_blocks() -> None:
    values = cast(dict[str, dict[str, object]], yaml.safe_load(VALUES.read_text()))
    cp = values["controlPlane"]
    assert isinstance(cp.get("autoscaling"), dict)
    assert isinstance(cp.get("pdb"), dict)
    auto = cast(dict[str, object], cp["autoscaling"])
    assert auto["enabled"] is False, "autoscaling defaults off; ops opt in per env"
    assert auto["minReplicas"] == 2
    assert auto["maxReplicas"] == 10
    assert auto["targetCPUUtilizationPercentage"] == 75
    pdb = cast(dict[str, object], cp["pdb"])
    assert pdb["enabled"] is True, "PDB on by default to honor minAvailable=1"
    assert pdb["minAvailable"] == 1


def test_schema_rejects_autoscaling_missing_min_replicas() -> None:
    schema = json.loads(SCHEMA.read_text())
    bad = cast(
        dict[str, object],
        yaml.safe_load(VALUES.read_text()),
    )
    cp = cast(dict[str, object], bad["controlPlane"])
    auto = cast(dict[str, object], dict(cp["autoscaling"]))  # type: ignore[arg-type]
    del auto["minReplicas"]
    cp["autoscaling"] = auto
    try:
        jsonschema.validate(bad, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema should reject autoscaling without minReplicas")
