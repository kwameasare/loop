"""Tests for the S780 cross-cloud nightly smoke."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from threading import Thread
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts" / "cross_cloud_smoke.py"
SERVER = ROOT / "scripts" / "helm_e2e_smoke_server.py"
WORKFLOW = ROOT / ".github" / "workflows" / "cross-cloud-smoke.yml"


def _run_smoke(
    port: int, *, cloud: str = "aws", region: str = "na-east"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SMOKE),
            "--cloud",
            cloud,
            "--region",
            region,
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--timeout",
            "5",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_cross_cloud_smoke_accepts_first_turn_for_all_cloud_labels() -> None:
    spec = importlib.util.spec_from_file_location("helm_smoke", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.make_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        for cloud, region in (("aws", "na-east"), ("azure", "eu-west"), ("gcp", "apac-sg")):
            result = _run_smoke(port, cloud=cloud, region=region)
            assert result.returncode == 0, result.stderr
            assert f"cross_cloud_smoke: OK cloud={cloud} region={region}" in result.stdout
    finally:
        server.shutdown()
        server.server_close()


def test_cross_cloud_smoke_rejects_unsupported_cloud() -> None:
    result = _run_smoke(9, cloud="oracle", region="na-east")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_cross_cloud_smoke_workflow_runs_nightly_matrix_and_pages() -> None:
    workflow = cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))
    triggers = cast(dict[Any, Any], workflow.get(True, workflow.get("on", {})))
    job = cast(dict[str, Any], workflow["jobs"]["cross-cloud-smoke"])
    matrix = cast(list[dict[str, Any]], job["strategy"]["matrix"]["include"])
    steps = cast(list[dict[str, Any]], job["steps"])
    runs = "\n".join(str(step.get("run", "")) for step in steps)

    assert triggers["schedule"][0]["cron"] == "17 5 * * *"
    assert "workflow_dispatch" in triggers
    assert job["strategy"]["fail-fast"] is False
    assert {item["cloud"] for item in matrix} == {"aws", "azure", "gcp"}
    assert "scripts/cross_cloud_smoke.sh" in runs
    assert "helm upgrade --install" in runs

    notify = next(step for step in steps if step.get("name") == "Page on-call")
    assert notify["if"] == "failure()"
    assert notify["env"]["LOOP_ONCALL_WEBHOOK_URL"] == "${{ secrets.LOOP_ONCALL_WEBHOOK_URL }}"
