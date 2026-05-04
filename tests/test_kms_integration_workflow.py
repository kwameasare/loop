"""Workflow checks for Vault transit + aws_kms integration CI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "kms-integration.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def test_kms_integration_workflow_path_filters_cover_kms_modules() -> None:
    data = _workflow()
    triggers = cast(dict[Any, Any], data.get(True, data.get("on", {})))
    pr_paths = cast(list[str], triggers["pull_request"]["paths"])

    assert "packages/control-plane/loop_control_plane/kms.py" in pr_paths
    assert "packages/control-plane/loop_control_plane/vault_transit.py" in pr_paths
    assert "packages/control-plane/loop_control_plane/aws_backends.py" in pr_paths


def test_kms_integration_workflow_starts_vault_and_localstack() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["kms-integration"])
    services = cast(dict[str, Any], job["services"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert services["vault"]["image"] == "hashicorp/vault:1.18"
    assert services["localstack"]["image"] == "localstack/localstack:3.7"
    assert "sys/mounts/transit" in runs
    assert "test_vault_transit_integration.py" in runs
    assert "test_aws_backends_integration.py" in runs
    integration_step = next(
        step for step in steps if step.get("name") == "Run Vault transit + AWS KMS integration tests"
    )
    env = cast(dict[str, str], integration_step["env"])
    assert env["LOOP_VAULT_INTEGRATION"] == "1"
    assert env["LOOP_AWS_INTEGRATION"] == "1"
