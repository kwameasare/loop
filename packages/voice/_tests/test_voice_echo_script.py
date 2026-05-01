"""S371 regression coverage for scripts/voice_echo_test.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "voice_echo_test.py"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_voice_echo_script_hears_agent_within_two_seconds() -> None:
    assert SCRIPT.exists(), "scripts/voice_echo_test.py must exist for S371"

    result = _run_script("--utterance", "status check", "--timeout-ms", "2000")

    assert result.returncode == 0, (
        f"voice_echo_test failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    summary = json.loads(result.stdout)
    assert summary["answer_kind"] == "answer"
    assert summary["participants_joined"] == ["caller", "echo-agent"]
    assert summary["utterance"] == "status check"
    assert summary["agent_text"] == "echo: status check"
    assert summary["outbound_text"] == "echo: status check"
    assert summary["elapsed_ms"] <= 2_000


def test_voice_echo_script_rejects_bad_offer() -> None:
    result = _run_script("--offer-sdp", "", "--timeout-ms", "2000")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "offer requires a non-empty sdp" in result.stderr
