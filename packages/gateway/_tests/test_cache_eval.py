"""Tests for the S841 gateway cache hit-ratio eval."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from loop_gateway.cache_eval import run_gateway_cache_eval

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "gateway_cache_hit_ratio.py"


@pytest.mark.asyncio
async def test_gateway_cache_eval_passes_fixed_workload() -> None:
    result = await run_gateway_cache_eval()

    assert result.requests == 10
    assert result.hits == 6
    assert result.misses == 4
    assert result.hit_ratio == 0.6
    assert result.passed is True


@pytest.mark.asyncio
async def test_gateway_cache_eval_fails_when_target_is_too_high() -> None:
    result = await run_gateway_cache_eval(min_hit_ratio=0.90)

    assert result.hit_ratio == 0.6
    assert result.passed is False


def test_gateway_cache_hit_ratio_script_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "gateway_cache_hit_ratio.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output), "--min-hit-ratio", "0.30"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(output.read_text())
    assert result.returncode == 0, result.stderr
    assert payload["name"] == "gateway_cache_hit_ratio_fixed_eval"
    assert payload["hit_ratio"] == 0.6
    assert payload["passed"] is True


def test_gateway_cache_hit_ratio_script_fails_below_target(tmp_path: Path) -> None:
    output = tmp_path / "gateway_cache_hit_ratio.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output), "--min-hit-ratio", "0.90"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "below 90.0%" in result.stderr
