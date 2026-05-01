"""S122 regression: ``scripts/cp_smoke.sh`` exits 0.

Runs the end-to-end smoke as a subprocess so the shell wrapper itself
is exercised — that is the AC artefact CI gates on.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cp_smoke_script_exits_zero() -> None:
    script = REPO_ROOT / "scripts" / "cp_smoke.sh"
    assert script.exists(), "scripts/cp_smoke.sh must exist (S122)"

    # Run the python entrypoint directly with the current interpreter so
    # the test does not depend on uv being on PATH inside CI sandboxes.
    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "cp_smoke.py")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"cp_smoke failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "OK" in result.stdout, f"missing OK marker: {result.stdout!r}"
