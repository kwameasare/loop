"""Checks for on-call schedule file and PagerDuty Terraform module wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "infra" / "oncall" / "schedule.yaml"
MODULE = ROOT / "infra" / "terraform" / "modules" / "pagerduty-oncall"
WORKFLOW = ROOT / ".github" / "workflows" / "oncall-schedule-validate.yml"


def test_schedule_yaml_contains_rotations_and_escalation() -> None:
    data = cast(dict[str, Any], yaml.safe_load(SCHEDULE.read_text()))

    assert data["team"] == "loop-infra"
    assert data["timezone"]
    rotations = cast(list[dict[str, Any]], data["rotations"])
    assert {rotation["name"] for rotation in rotations} == {"primary", "secondary"}
    assert all(rotation["users"] for rotation in rotations)
    escalation = cast(list[dict[str, Any]], data["escalation"])
    assert [rule["target"] for rule in escalation] == ["primary", "secondary"]


def test_pagerduty_module_files_exist_and_reference_schedule_yaml() -> None:
    main_tf = (MODULE / "main.tf").read_text()
    variables_tf = (MODULE / "variables.tf").read_text()
    outputs_tf = (MODULE / "outputs.tf").read_text()

    assert "pagerduty/pagerduty" in main_tf
    assert "yamldecode(file(var.schedule_file))" in main_tf
    assert 'resource "pagerduty_schedule" "rotation"' in main_tf
    assert 'resource "pagerduty_escalation_policy" "oncall"' in main_tf
    assert 'variable "schedule_file"' in variables_tf
    assert 'output "schedule_ids"' in outputs_tf
    assert 'output "escalation_policy_id"' in outputs_tf


def test_oncall_schedule_validation_workflow_exists() -> None:
    data = cast(dict[str, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    job = cast(dict[str, Any], data["jobs"]["oncall-schedule-validate"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    assert "pull_request" in triggers
    assert "infra/oncall/schedule.yaml" in triggers["pull_request"]["paths"]
    assert "tools/validate_oncall_schedule.py" in runs
