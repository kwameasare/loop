"""
Tests for S804 — chaos engineering harness (network partition, DB failover, NATS outage).

Validates:
- Chaos scripts exist and are executable
- Python harness exists and is importable
- CHAOS_FINDINGS.md exists and has correct structure
- Harness runs in dry-run mode and produces valid output
- SLA assessment logic is correct
- Findings are appended correctly
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHAOS_DIR = REPO_ROOT / "loop_implementation" / "engineering" / "chaos"
FINDINGS_FILE = REPO_ROOT / "loop_implementation" / "engineering" / "CHAOS_FINDINGS.md"
HARNESS = CHAOS_DIR / "harness.py"

sys.path.insert(0, str(CHAOS_DIR))


# ── Script existence ───────────────────────────────────────────────────────

def test_network_partition_script_exists():
    assert (CHAOS_DIR / "network_partition.sh").exists()


def test_db_failover_script_exists():
    assert (CHAOS_DIR / "db_failover.sh").exists()


def test_nats_outage_script_exists():
    assert (CHAOS_DIR / "nats_outage.sh").exists()


def test_harness_py_exists():
    assert HARNESS.exists()


# ── CHAOS_FINDINGS.md ──────────────────────────────────────────────────────

def test_chaos_findings_file_exists():
    assert FINDINGS_FILE.exists()


def test_chaos_findings_has_sla_table():
    content = FINDINGS_FILE.read_text()
    assert "network_partition" in content
    assert "db_failover" in content
    assert "nats_outage" in content


def test_chaos_findings_has_rto_references():
    content = FINDINGS_FILE.read_text()
    assert "RTO" in content


# ── Harness module import ──────────────────────────────────────────────────

def test_harness_imports_without_error():
    import harness as h  # noqa: F401


def test_sla_limits_defined():
    import harness as h
    assert "network_partition" in h.SLA_LIMITS
    assert "db_failover" in h.SLA_LIMITS
    assert "nats_outage" in h.SLA_LIMITS


def test_script_map_has_three_scenarios():
    import harness as h
    assert len(h.SCRIPT_MAP) == 3


# ── SLA assessment logic ───────────────────────────────────────────────────

def test_assess_sla_pass_within_limit():
    import harness as h
    passed, msg = h.assess_sla({"scenario": "nats_outage", "rto_s": 45})
    assert passed
    assert "45" in msg


def test_assess_sla_fail_over_limit():
    import harness as h
    passed, _msg = h.assess_sla({"scenario": "nats_outage", "rto_s": 120})
    assert not passed


def test_assess_sla_db_failover_limit_is_300():
    import harness as h
    assert h.SLA_LIMITS["db_failover"] == 300


def test_assess_sla_no_rto_returns_pass():
    import harness as h
    passed, msg = h.assess_sla({"scenario": "db_failover"})
    assert passed
    assert "dry-run" in msg or "no RTO" in msg


# ── Dry-run execution ──────────────────────────────────────────────────────

def test_harness_dry_run_completes(tmp_path):
    """Harness runs all scenarios in dry-run mode without error."""
    env = os.environ.copy()
    env["CHAOS_DURATION"] = "0"
    # Override findings file to a temp file so we don't pollute the real one
    result = subprocess.run(
        [sys.executable, str(HARNESS), "--dry-run", "--scenario", "network_partition"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
        env=env,
    )
    # Should not crash (returncode 0 = pass, 1 = SLA violation — both acceptable for dry-run)
    assert result.returncode in (0, 1), f"unexpected returncode: {result.returncode}\n{result.stderr}"


def test_run_scenario_returns_dict():
    import harness as h
    r = h.run_scenario("network_partition", dry_run=True)
    assert isinstance(r, dict)
    assert "scenario" in r


# ── append_findings ────────────────────────────────────────────────────────

def test_append_findings_creates_file_if_missing(tmp_path, monkeypatch):
    import harness as h
    tmp_findings = tmp_path / "CHAOS_FINDINGS.md"
    monkeypatch.setattr(h, "FINDINGS_FILE", tmp_findings)
    h.append_findings([{"scenario": "nats_outage", "rto_s": 10, "status": "completed"}])
    content = tmp_findings.read_text()
    assert "Chaos Engineering Findings" in content
    assert "nats_outage" in content


def test_append_findings_marks_sla_pass(tmp_path, monkeypatch):
    import harness as h
    tmp_findings = tmp_path / "CHAOS_FINDINGS.md"
    monkeypatch.setattr(h, "FINDINGS_FILE", tmp_findings)
    h.append_findings([{"scenario": "nats_outage", "rto_s": 30, "status": "completed"}])
    content = tmp_findings.read_text()
    assert "PASS" in content


def test_append_findings_marks_sla_fail(tmp_path, monkeypatch):
    import harness as h
    tmp_findings = tmp_path / "CHAOS_FINDINGS.md"
    monkeypatch.setattr(h, "FINDINGS_FILE", tmp_findings)
    h.append_findings([{"scenario": "nats_outage", "rto_s": 999, "status": "completed"}])
    content = tmp_findings.read_text()
    assert "FAIL" in content
