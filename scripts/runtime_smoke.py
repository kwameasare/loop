"""S143: end-to-end smoke for the dp-runtime image entrypoint.

The S143 acceptance criterion is *the smoke script exits 0; CI runs
it after deploy*. The dp-runtime container ships only the entrypoint
defined in ``loop_data_plane.__main__`` plus the alembic migration
chain — runtime business logic is being landed in subsequent slices.

This script exercises both surfaces:

    1. Boot the entrypoint (``python -m loop_data_plane``) and assert
       it prints the expected version banner and exits 0 — this is
       the same call the distroless image runs as ``CMD``.
    2. Resolve the migration head revision via alembic so a missing
       or broken migrations directory in the deployed image trips the
       smoke.

Each step asserts on observable output so a regression in either the
entrypoint or migrations packaging fails fast. Exits 0 with a
``OK`` summary on success.

Run via ``scripts/runtime_smoke.sh`` (which CI invokes) or directly
with ``uv run python scripts/runtime_smoke.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_entrypoint() -> str:
    """Run ``python -m loop_data_plane`` and return its stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "loop_data_plane"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"entrypoint exited {result.returncode}: stderr={result.stderr!r}")
    return result.stdout


def _resolve_alembic_head() -> str:
    """Return the alembic head revision id for the dp migration chain."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg_path = (
        REPO_ROOT / "packages" / "data-plane" / "loop_data_plane" / "migrations" / "alembic.ini"
    )
    if not cfg_path.exists():
        raise AssertionError(f"missing alembic.ini at {cfg_path}")
    cfg = Config(str(cfg_path))
    cfg.set_main_option(
        "script_location",
        str(cfg_path.parent),
    )
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    if head is None:
        raise AssertionError("alembic chain has no head revision")
    return head


def main() -> int:
    try:
        stdout = _run_entrypoint()
        if "loop-data-plane" not in stdout:
            raise AssertionError(f"entrypoint stdout missing banner: {stdout!r}")
        head = _resolve_alembic_head()
        if not head:
            raise AssertionError("alembic head was empty")
    except AssertionError as exc:
        sys.stderr.write(f"runtime_smoke: FAIL {exc}\n")
        return 1
    sys.stdout.write(f"runtime_smoke: OK head={head}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
