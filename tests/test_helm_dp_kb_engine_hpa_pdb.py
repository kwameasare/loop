"""Smoke tests for dp-kb-engine Helm templates added in S445."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
DEPLOYMENT = CHART / "templates" / "kb-engine.yaml"
HPA = CHART / "templates" / "kb-engine-hpa.yaml"
PDB = CHART / "templates" / "kb-engine-pdb.yaml"
CONFIGMAP = CHART / "templates" / "configmap.yaml"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def test_kb_engine_deployment_template_renders_service_shape() -> None:
    text = DEPLOYMENT.read_text()
    assert "{{- if .Values.kbEngine.enabled }}" in text
    assert "kind: Deployment" in text
    assert "kind: Service" in text
    assert ".Values.kbEngine.replicaCount" in text
    assert ".Values.kbEngine.service.port" in text
    assert "app.kubernetes.io/component: kb-engine" in text
    assert 'name: {{ include "loop.fullname" . }}-kb-engine' in text


def test_kb_engine_hpa_template_targets_kb_engine_deployment() -> None:
    text = HPA.read_text()
    assert "apiVersion: autoscaling/v2" in text
    assert "kind: HorizontalPodAutoscaler" in text
    assert ".Values.kbEngine.enabled" in text
    assert ".Values.kbEngine.autoscaling.enabled" in text
    assert "-kb-engine" in text
    assert "kind: Deployment" in text


def test_kb_engine_pdb_template_uses_xor_min_max() -> None:
    text = PDB.read_text()
    assert "apiVersion: policy/v1" in text
    assert "kind: PodDisruptionBudget" in text
    assert ".Values.kbEngine.pdb.enabled" in text
    assert "minAvailable" in text and "maxUnavailable" in text
    assert "{{- else if" in text
    assert "app.kubernetes.io/component: kb-engine" in text


def test_configmap_wires_runtime_and_kb_engine_urls() -> None:
    text = CONFIGMAP.read_text()
    assert "LOOP_RUNTIME_KB_URL" in text
    assert "LOOP_KB_PORT" in text
    assert "LOOP_KB_QDRANT_URL" in text
    assert ".Values.kbEngine.service.port" in text
    assert ".Values.externals.qdrantUrl" in text


def test_kb_engine_values_have_autoscaling_and_pdb_blocks() -> None:
    values = cast(dict[str, dict[str, object]], yaml.safe_load(VALUES.read_text()))
    kb = values["kbEngine"]
    assert kb["enabled"] is True
    assert cast(dict[str, object], kb["service"])["port"] == 8003
    auto = cast(dict[str, object], kb["autoscaling"])
    assert auto["enabled"] is False
    assert auto["minReplicas"] == 2
    assert auto["maxReplicas"] == 20
    assert auto["targetCPUUtilizationPercentage"] == 70
    pdb = cast(dict[str, object], kb["pdb"])
    assert pdb["enabled"] is True
    assert pdb["minAvailable"] == 1


def test_kb_engine_schema_rejects_invalid_service_port() -> None:
    schema = json.loads(SCHEMA.read_text())
    bad = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    kb = cast(dict[str, object], bad["kbEngine"])
    service = cast(dict[str, object], dict(kb["service"]))  # type: ignore[arg-type]
    service["port"] = 70000
    kb["service"] = service
    try:
        jsonschema.validate(bad, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema should reject kbEngine.service.port > 65535")
