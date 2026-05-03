"""S143/S902: end-to-end smoke for the dp-runtime image entrypoint.

The S143 acceptance criterion is *the smoke script exits 0; CI runs
it after deploy*. S902 replaces the old ``python -m loop_data_plane``
banner stub with a real Uvicorn process serving ``runtime_app:app``.

This script exercises both surfaces:

    1. Boot the Uvicorn app and assert ``/healthz`` returns 200.
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

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _probe_runtime() -> None:
    """Run Uvicorn briefly and assert the health route responds."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "loop_data_plane.runtime_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 20
        last_error = ""
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                raise AssertionError(f"uvicorn exited early: {stderr}")
            try:
                with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as response:
                    if response.status == 200:
                        return
            except OSError as exc:
                last_error = str(exc)
            time.sleep(0.2)
        raise AssertionError(f"runtime app did not become ready: {last_error}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


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
        _probe_runtime()
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
