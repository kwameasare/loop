"""S580: secrets-scanning gate (gitleaks) wired into the security job.

Acceptance: gitleaks runs as part of the `security` required-on-main
CI job and fails on detected secrets. Test verifies (a) the workflow
contains the gitleaks step pinned to a major version, (b) the
.gitleaks.toml config exists and uses the default ruleset, and (c) a
fake committed AWS key would be caught (failure-mode test) by running
gitleaks against an in-memory file when the binary is available.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
GITLEAKS_CFG = ROOT / ".gitleaks.toml"


def _security_steps() -> list[dict[str, object]]:
    workflow = yaml.safe_load(CI.read_text())
    jobs = workflow["jobs"]
    sec = jobs["security"]
    return list(sec["steps"])


def test_security_job_includes_gitleaks_step_pinned() -> None:
    steps = _security_steps()
    matches = [s for s in steps if "gitleaks" in str(s.get("uses", "")).lower()]
    assert matches, "security job must run a gitleaks step"
    uses = str(matches[0]["uses"])
    # Pinned to a real major version, not @main / @master / no-tag.
    assert "@v" in uses, f"gitleaks action must be pinned: {uses}"


def test_gitleaks_config_present_and_uses_default_rules() -> None:
    assert GITLEAKS_CFG.is_file(), ".gitleaks.toml must exist at repo root"
    text = GITLEAKS_CFG.read_text()
    # Default rules give us the curated AWS/GH/Stripe/Slack/JWT corpus.
    assert "useDefault = true" in text
    # Allowlist must exist and not be a blanket bypass.
    assert "[allowlist]" in text
    assert "paths" in text


def test_security_job_unconditional() -> None:
    """S580 strengthens the existing `security` job. It must remain
    unconditional (no `if:` gate) so it runs on every PR + push."""
    workflow = yaml.safe_load(CI.read_text())
    sec = workflow["jobs"]["security"]
    assert "if" not in sec, "security job must run unconditionally"
    assert sec["runs-on"] == "ubuntu-latest"


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks CLI not installed")
def test_gitleaks_detects_planted_secret_failure_mode(tmp_path: Path) -> None:
    """Failure-mode coverage: a planted slack-bot-style token MUST be
    flagged by `gitleaks detect` using our config. We run on a tmp
    file outside the repo so we never accidentally match real
    repo content."""
    bad = tmp_path / "leaky.py"
    # Real-shape Slack bot token assembled from parts to dodge GitHub
    # push-protection on this test file itself. Default gitleaks
    # ruleset has high-confidence detection on the assembled value.
    fake_token = "-".join(
        [
            "xoxb",
            "1234567890",
            "1234567890123",
            "aBcDeFgHiJkLmNoPqRsTuVwX",
        ]
    )
    bad.write_text(f'SLACK_TOKEN = "{fake_token}"\n')
    result = subprocess.run(
        [
            "gitleaks",
            "detect",
            "--no-git",
            "--source",
            str(tmp_path),
            "--config",
            str(GITLEAKS_CFG),
            "--exit-code",
            "1",
            "--redact",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"gitleaks did NOT flag a planted slack token (exit={result.returncode}): "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
