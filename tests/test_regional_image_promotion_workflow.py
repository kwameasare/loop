"""Regional image promotion workflow checks (S595)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "promote-regional-images.yml"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))


def test_workflow_runs_daily_and_manually() -> None:
    on = cast(dict[str, Any], _workflow().get(True, _workflow().get("on", {})))

    assert "workflow_dispatch" in on
    assert {"cron": "17 4 * * *"} in on["schedule"]


def test_workflow_has_keyless_signing_permissions() -> None:
    workflow = _workflow()

    assert workflow["permissions"]["id-token"] == "write"
    assert workflow["permissions"]["packages"] == "write"


def test_promotes_same_digest_to_na_and_eu_regions() -> None:
    workflow = _workflow()
    job = cast(dict[str, Any], workflow["jobs"]["promote"])
    text = yaml.safe_dump(job)
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))

    env = cast(dict[str, str], workflow["env"])
    assert env["REGIONS"] == "na-east eu-west"
    assert env["SERVICES"] == "cp-api dp-runtime"
    assert "crane digest" in text
    assert "cosign sign --yes" in text
    assert "cosign verify" in text
    assert "crane copy" in text
    assert 'test "${promoted}" = "${digest}"' in runs
    assert "regional-image-digests.txt" in text


def test_workflow_requires_production_approval_environment() -> None:
    workflow = _workflow()
    job = cast(dict[str, Any], workflow["jobs"]["promote"])

    assert job["environment"] == "production-image-promotion"


def test_policy_rejects_workflow_without_digest_equality_check() -> None:
    workflow = _workflow()
    job = cast(dict[str, Any], workflow["jobs"]["promote"])
    runs = "\n".join(str(step.get("run", "")) for step in cast(list[dict[str, Any]], job["steps"]))
    broken = runs.replace('test "${promoted}" = "${digest}"', "")

    assert "crane copy" in broken
    assert 'test "${promoted}" = "${digest}"' not in broken
