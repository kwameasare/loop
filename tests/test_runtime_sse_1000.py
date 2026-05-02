"""Tests for the S844 runtime SSE 1000-concurrency gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from threading import Thread
from typing import Any, cast
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "k6_runtime_sse_1000.js"
WORKFLOW = ROOT / ".github" / "workflows" / "runtime-sse-1000.yml"
RESULT = ROOT / "bench" / "results" / "runtime_sse_1000_concurrency.json"
SERVER = ROOT / "scripts" / "helm_e2e_smoke_server.py"


def _workflow() -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(WORKFLOW.read_text()))


def _step_runs(job: dict[str, Any]) -> str:
    steps = cast(list[dict[str, Any]], job["steps"])
    return "\n".join(str(step.get("run", "")) for step in steps)


def test_k6_runtime_sse_script_enforces_1000_concurrency_budget() -> None:
    script = SCRIPT.read_text()

    assert "const CONCURRENT_TURNS = 1000" in script
    assert "const RUNTIME_SSE_P95_MS = 3000" in script
    assert "vus: CONCURRENT_TURNS" in script
    assert "/v1/turns/stream" in script
    assert "text/event-stream" in script
    assert "event: done" in script


def test_runtime_sse_workflow_runs_k6_and_memory_probe() -> None:
    data = _workflow()
    job = cast(dict[str, Any], data["jobs"]["runtime-sse-1000"])
    triggers = cast(dict[str, Any], data.get(True, data.get("on", {})))
    runs = _step_runs(job)

    assert triggers["schedule"][0]["cron"] == "7 6 * * *"
    assert "workflow_dispatch" in triggers
    assert job["env"]["LOOP_RUNTIME_SSE_MAX_MEMORY_BYTES"] == "4294967296"
    assert "k6 run --summary-export /tmp/runtime-sse-1000-summary.json" in runs
    assert "scripts/k6_runtime_sse_1000.js" in runs
    assert "memory.current" in runs
    assert "LOOP_ONCALL_WEBHOOK_URL" in runs


def test_runtime_sse_contract_result_matches_budgets() -> None:
    result = json.loads(RESULT.read_text())

    assert result["name"] == "runtime_sse_1000_concurrency"
    assert result["stats"]["concurrent_turns"] == 1000
    assert result["stats"]["p95_ms"] < result["budgets"]["p95_ms"]
    assert result["stats"]["memory_bytes"] < result["budgets"]["memory_bytes"]
    assert result["stats"]["http_req_failed_rate"] < result["budgets"]["http_req_failed_rate"]


def test_smoke_server_serves_sse_turn_stream() -> None:
    spec = importlib.util.spec_from_file_location("helm_smoke", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.make_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        request = Request(
            f"http://127.0.0.1:{port}/v1/turns/stream",
            data=b'{"input":"hello"}',
            headers={"accept": "text/event-stream"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            body = response.read().decode()
            assert response.headers["content-type"] == "text/event-stream"
            assert "event: delta" in body
            assert "event: done" in body
    finally:
        server.shutdown()
        server.server_close()
