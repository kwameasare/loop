"""Smoke tests for the docs site v0 nav manifest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_check_docs_links_passes() -> None:
    """The repo's docs/ tree satisfies its own link-validation rules."""

    result = subprocess.run(
        [sys.executable, "tools/check_docs_links.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_docs_links.py failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "docs-links: ok" in result.stdout


def test_index_lists_required_concept_pages() -> None:
    index = (REPO_ROOT / "docs" / "index.md").read_text()
    for page in (
        "concepts/agents.md",
        "concepts/tools.md",
        "concepts/memory.md",
        "concepts/channels.md",
        "concepts/eval.md",
        "quickstart.md",
        "cookbook/support_agent.md",
    ):
        assert page in index, f"docs/index.md is missing {page}"


def test_support_agent_has_readme_and_run_eval() -> None:
    base = REPO_ROOT / "examples" / "support_agent"
    assert (base / "README.md").exists()
    assert (base / "run_eval.py").exists()
    assert (base / ".env.example").exists()
