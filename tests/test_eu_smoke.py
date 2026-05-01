"""Tests for the S597 EU-west full-turn smoke script."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts" / "eu_smoke.py"
SERVER = ROOT / "scripts" / "helm_e2e_smoke_server.py"


def _run_smoke(port: int, **overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {
        "EU_SMOKE_BASE_URL": f"http://127.0.0.1:{port}",
        "EU_SMOKE_REGION": "eu-west",
        "EU_SMOKE_TIMEOUT_SECONDS": "5",
    }
    env.update(overrides)
    return subprocess.run(
        [sys.executable, str(SMOKE)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_eu_smoke_script_accepts_eu_west_full_turn() -> None:
    spec = importlib.util.spec_from_file_location("helm_smoke", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.make_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        result = _run_smoke(port)
        assert result.returncode == 0, result.stderr
        assert "eu_smoke: OK region=eu-west" in result.stdout
    finally:
        server.shutdown()
        server.server_close()


def test_eu_smoke_script_rejects_non_eu_region() -> None:
    result = _run_smoke(9, EU_SMOKE_REGION="us-east")
    assert result.returncode == 1
    assert "must target eu-west" in result.stderr
