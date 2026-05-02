"""Tests for the S843 tool-host warm-start benchmark."""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest
from loop_tool_host.pool import (
    DEFAULT_ACQUIRE_TIMEOUT_SECONDS,
    DEFAULT_MAX_SIZE,
    DEFAULT_MIN_IDLE,
    WarmPool,
)
from loop_tool_host.warm_start_bench import run_warm_start_bench

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "tool_host_warm_start.py"


def test_warm_pool_defaults_are_tuned_for_warm_start() -> None:
    assert DEFAULT_MIN_IDLE == 2
    assert DEFAULT_MAX_SIZE == 8
    assert DEFAULT_ACQUIRE_TIMEOUT_SECONDS == 0.3
    params = inspect.signature(WarmPool).parameters
    assert params["min_idle"].default == DEFAULT_MIN_IDLE
    assert params["max_size"].default == DEFAULT_MAX_SIZE


@pytest.mark.asyncio
async def test_warm_start_bench_passes_300ms_budget() -> None:
    result = await run_warm_start_bench(iterations=8, target_p95_ms=300)

    assert result.iterations == 8
    assert result.p95_ms < 300
    assert result.passed is True


@pytest.mark.asyncio
async def test_warm_start_bench_rejects_empty_runs() -> None:
    with pytest.raises(ValueError, match="iterations"):
        await run_warm_start_bench(iterations=0)


def test_tool_host_warm_start_script_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "tool_host_warm_start.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output), "--iterations", "8"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(output.read_text())
    assert result.returncode == 0, result.stderr
    assert payload["name"] == "tool_host_warm_start"
    assert payload["target_p95_ms"] == 300
    assert payload["passed"] is True
