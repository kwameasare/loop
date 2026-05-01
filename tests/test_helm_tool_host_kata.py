"""Tests for the dp-tool-host Helm subchart and Kata RuntimeClass hook (S444)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
SUBCHART = CHART / "charts" / "dp-tool-host"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def _load_yaml(path: Path) -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(path.read_text()))


def test_parent_chart_registers_tool_host_subchart() -> None:
    chart = _load_yaml(CHART / "Chart.yaml")
    deps = cast(list[dict[str, object]], chart["dependencies"])
    tool_host = next(d for d in deps if d["name"] == "dp-tool-host")
    assert tool_host["alias"] == "toolHost"
    assert tool_host["condition"] == "toolHost.enabled"
    assert tool_host["repository"] == "file://charts/dp-tool-host"
    assert (SUBCHART / "Chart.yaml").is_file()


def test_values_default_tool_host_requires_kata_firecracker() -> None:
    values = _load_yaml(VALUES)
    tool_host = cast(dict[str, object], values["toolHost"])
    kata = cast(dict[str, object], tool_host["kata"])
    check = cast(dict[str, object], tool_host["preInstallCheck"])
    assert tool_host["enabled"] is True
    assert tool_host["sandboxRuntimeClassName"] == "loop-firecracker"
    assert kata == {"required": True, "runtimeClassHandler": "kata-fc"}
    assert check["enabled"] is True
    assert "kubectl" in cast(str, check["image"])


def test_subchart_deployment_exports_sandbox_runtime_class() -> None:
    template = (SUBCHART / "templates" / "deployment.yaml").read_text()
    assert "{{- if .Values.enabled }}" in template
    assert "kind: Deployment" in template
    assert "kind: Service" in template
    assert "app.kubernetes.io/component: dp-tool-host" in template
    assert "LOOP_TOOL_HOST_SANDBOX_RUNTIME_CLASS" in template
    assert ".Values.sandboxRuntimeClassName | quote" in template


def test_preinstall_hook_checks_runtimeclass_with_clear_error() -> None:
    template = (SUBCHART / "templates" / "kata-check-job.yaml").read_text()
    assert ".Values.preInstallCheck.enabled" in template
    assert '"helm.sh/hook": pre-install,pre-upgrade' in template
    assert "kubectl get runtimeclass" in template
    assert "requires Kubernetes RuntimeClass" in template
    assert "backed by Kata Containers/Firecracker" in template
    assert "set toolHost.enabled=false" in template
    assert "does not match required Kata handler" in template


def test_preinstall_rbac_can_read_runtimeclasses_only() -> None:
    template = (SUBCHART / "templates" / "kata-check-rbac.yaml").read_text()
    assert "kind: ClusterRole" in template
    assert 'apiGroups: ["node.k8s.io"]' in template
    assert 'resources: ["runtimeclasses"]' in template
    assert 'verbs: ["get"]' in template
    assert "hook-delete-policy" in template


def test_values_schema_rejects_missing_runtimeclass() -> None:
    schema = json.loads(SCHEMA.read_text())
    bad = copy.deepcopy(_load_yaml(VALUES))
    tool_host = cast(dict[str, object], bad["toolHost"])
    del tool_host["sandboxRuntimeClassName"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
