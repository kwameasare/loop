"""S914: hermetic tests for the scripts/demo/ scripted demos.

We deliberately do not invoke real LLM providers from the test suite.
Instead, we exercise the dry-run path (``LOOP_DEMO_DRY_RUN=1``) which
each script honours by streaming its recorded "expected" transcript
to stdout. This keeps CI green while still asserting:

* the five demo scripts exist with the names called out in the AC,
* every script is executable, sources ``_lib.sh`` and uses
  ``set -euo pipefail``,
* every script ships a recorded transcript and produces it verbatim
  in dry-run mode,
* the README documents the prerequisites and lists every demo.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "scripts" / "demo"

DEMO_SCRIPTS: tuple[tuple[str, str], ...] = (
    ("1_chat.sh", "1_chat.txt"),
    ("2_tool.sh", "2_tool.txt"),
    ("3_kb.sh", "3_kb.txt"),
    ("4_multiagent.sh", "4_multiagent.txt"),
    ("5_hitl.sh", "5_hitl.txt"),
)


def test_demo_dir_exists() -> None:
    assert DEMO_DIR.is_dir(), f"missing {DEMO_DIR}"
    assert (DEMO_DIR / "_lib.sh").is_file(), "missing scripts/demo/_lib.sh"
    assert (DEMO_DIR / "README.md").is_file(), "missing scripts/demo/README.md"


@pytest.mark.parametrize(("script", "expected"), DEMO_SCRIPTS)
def test_demo_script_metadata(script: str, expected: str) -> None:
    path = DEMO_DIR / script
    assert path.is_file(), f"missing demo script {path}"
    mode = path.stat().st_mode
    assert mode & stat.S_IXUSR, f"{script} is not executable"
    body = path.read_text(encoding="utf-8")
    assert body.startswith("#!/usr/bin/env bash"), f"{script} missing shebang"
    assert "set -euo pipefail" in body, f"{script} missing strict bash mode"
    assert 'source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"' in body, (
        f"{script} does not source _lib.sh"
    )
    recorded = DEMO_DIR / "expected" / expected
    assert recorded.is_file(), f"missing recorded transcript {recorded}"


@pytest.mark.parametrize(("script", "expected"), DEMO_SCRIPTS)
def test_demo_script_dry_run_matches_recording(script: str, expected: str) -> None:
    recorded = (DEMO_DIR / "expected" / expected).read_text(encoding="utf-8")
    env = {**os.environ, "LOOP_DEMO_DRY_RUN": "1"}
    proc = subprocess.run(
        ["bash", str(DEMO_DIR / script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, (
        f"{script} exited {proc.returncode}: stderr={proc.stderr!r}"
    )
    # Strip the ANSI banner the helper prints; we only assert on the
    # recorded body to avoid coupling tests to the cosmetic header.
    assert recorded.strip() in proc.stdout, (
        f"{script} did not stream its recorded transcript;\n"
        f"stdout was:\n{proc.stdout}"
    )


def test_readme_documents_each_demo() -> None:
    readme = (DEMO_DIR / "README.md").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in readme, "README must mention OPENAI_API_KEY"
    assert "ANTHROPIC_API_KEY" in readme, "README must mention ANTHROPIC_API_KEY"
    assert "LOOP_DEMO_DRY_RUN" in readme, "README must document the dry-run env var"
    for script, _ in DEMO_SCRIPTS:
        assert script in readme, f"README does not mention {script}"
    # The AC ties the demos to G7; make sure the README keeps that link.
    assert "G7" in readme
    assert "examples/support_agent" in readme
