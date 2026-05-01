"""Tests for the Helm kind smoke workflow added in S453."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from threading import Thread
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "helm-e2e.yml"
SERVER = ROOT / "scripts" / "helm_e2e_smoke_server.py"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def _step_runs(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def test_helm_e2e_workflow_uses_kind_and_timeout_budget() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["helm-e2e"])
    steps = cast(list[dict[str, Any]], job["steps"])
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    assert job["timeout-minutes"] == 12
    assert any(step.get("uses") == "helm/kind-action@v1.10.0" for step in steps)
    assert any(step.get("uses") == "azure/setup-helm@v4" for step in steps)
    assert "workflow_dispatch" in triggers
    assert "schedule" in triggers


def test_helm_e2e_installs_chart_and_sends_turn() -> None:
    runs = _step_runs(cast(dict[str, Any], _workflow()["jobs"]["helm-e2e"]))
    assert "helm dependency build infra/helm/loop" in runs
    assert "helm upgrade --install loop infra/helm/loop" in runs
    assert "--wait --timeout 8m" in runs
    assert "toolHost.enabled=false" in runs
    assert "postgresql.enabled=false" in runs
    assert "kubectl port-forward svc/loop-loop-runtime 18081:8081" in runs
    assert "POST http://127.0.0.1:18081/v1/turns" in runs
    assert "helm-e2e-ok" in runs


def test_smoke_server_health_turn_and_not_found_paths() -> None:
    spec = importlib.util.spec_from_file_location("helm_smoke", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.make_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
            assert json.loads(response.read()) == {"ok": True}

        request = Request(
            f"http://127.0.0.1:{port}/v1/turns",
            data=b'{"input":"hello"}',
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            body = json.loads(response.read())
            assert body["reply"]["text"] == "helm-e2e-ok"
            assert body["received"] == '{"input":"hello"}'

        try:
            urlopen(f"http://127.0.0.1:{port}/missing", timeout=2)
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("missing path should return 404")
    finally:
        server.shutdown()
        server.server_close()
