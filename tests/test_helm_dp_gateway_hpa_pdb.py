"""Smoke tests for dp-gateway HPA + PDB templates added in S443."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
HPA = CHART / "templates" / "gateway-hpa.yaml"
PDB = CHART / "templates" / "gateway-pdb.yaml"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def test_gateway_hpa_template_targets_gateway_deployment() -> None:
    text = HPA.read_text()
    assert "apiVersion: autoscaling/v2" in text
    assert "kind: HorizontalPodAutoscaler" in text
    assert ".Values.gateway.enabled" in text
    assert ".Values.gateway.autoscaling.enabled" in text
    assert "-gateway" in text
    assert "kind: Deployment" in text


def test_gateway_pdb_template_uses_xor_min_max() -> None:
    text = PDB.read_text()
    assert "apiVersion: policy/v1" in text
    assert "kind: PodDisruptionBudget" in text
    assert ".Values.gateway.pdb.enabled" in text
    assert "minAvailable" in text and "maxUnavailable" in text
    assert "{{- else if" in text
    assert "app.kubernetes.io/component: gateway" in text


def test_gateway_values_have_autoscaling_and_pdb_blocks() -> None:
    values = cast(dict[str, dict[str, object]], yaml.safe_load(VALUES.read_text()))
    gw = values["gateway"]
    auto = cast(dict[str, object], gw["autoscaling"])
    assert auto["enabled"] is False
    assert auto["minReplicas"] == 2
    assert auto["maxReplicas"] == 20
    assert auto["targetCPUUtilizationPercentage"] == 70
    pdb = cast(dict[str, object], gw["pdb"])
    assert pdb["enabled"] is True
    assert pdb["minAvailable"] == 1


def test_gateway_schema_rejects_negative_min_replicas() -> None:
    schema = json.loads(SCHEMA.read_text())
    bad = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    gw = cast(dict[str, object], bad["gateway"])
    auto = cast(dict[str, object], dict(gw["autoscaling"]))  # type: ignore[arg-type]
    auto["minReplicas"] = -1
    gw["autoscaling"] = auto
    try:
        jsonschema.validate(bad, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema should reject negative minReplicas")
