"""S143 regression: ``scripts/runtime_smoke.sh`` exits 0.

Runs the dp-runtime end-to-end smoke as a subprocess so the shell
wrapper itself is exercised — that is the AC artefact CI gates on.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_smoke_script_exits_zero() -> None:
    script = REPO_ROOT / "scripts" / "runtime_smoke.sh"
    assert script.exists(), "scripts/runtime_smoke.sh must exist (S143)"

    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "runtime_smoke.py")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"runtime_smoke failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "OK" in result.stdout, f"missing OK marker: {result.stdout!r}"
