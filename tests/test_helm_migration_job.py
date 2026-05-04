"""Contract tests for the helm pre-install/pre-upgrade migration Job.

Closes P0.6c (audit: "no alembic migration mechanism in the chart").
Without this hook, fresh installs and upgrades crash-loop until tables
exist, and racing replicas corrupt the alembic state.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB_TEMPLATE = ROOT / "infra" / "helm" / "loop" / "templates" / "migration-job.yaml"
VALUES = ROOT / "infra" / "helm" / "loop" / "values.yaml"


def _job_body() -> str:
    return JOB_TEMPLATE.read_text(encoding="utf-8")


def test_migration_job_template_exists() -> None:
    assert JOB_TEMPLATE.is_file()


def test_migration_job_runs_pre_install_and_pre_upgrade() -> None:
    body = _job_body()
    # Must run before pods boot in both flows
    assert "helm.sh/hook: pre-install,pre-upgrade" in body
    # Hook weight must place it before service Deployments
    assert 'helm.sh/hook-weight: "-5"' in body


def test_migration_job_has_pg_advisory_lock() -> None:
    """Concurrent helm operations against the same DB must serialise.
    The advisory lock prevents two replicas racing the same upgrade."""
    body = _job_body()
    assert "pg_advisory_lock" in body
    assert "pg_advisory_unlock" in body


def test_migration_job_runs_both_planes() -> None:
    """Both cp-api and dp-runtime migrations must run from the same Job
    so the deployment is atomic from the operator's perspective."""
    body = _job_body()
    assert "loop_control_plane.migrations" in body
    assert "loop_data_plane.migrations" in body


def test_migration_job_uses_pod_security_helpers() -> None:
    """Same hardening as the service pods — read-only FS, drop caps,
    runAsNonRoot."""
    body = _job_body()
    assert 'include "loop.podSecurityContext"' in body
    assert 'include "loop.containerSecurityContext"' in body


def test_migration_job_cleanup_policy() -> None:
    """Stuck-Failed Jobs must be deleted before the next attempt;
    succeeded Jobs cleaned up by ttlSecondsAfterFinished + the
    delete-policy."""
    body = _job_body()
    assert "before-hook-creation,hook-succeeded" in body
    assert "ttlSecondsAfterFinished" in body


def test_values_declares_migrations_block() -> None:
    body = VALUES.read_text(encoding="utf-8")
    assert "migrations:" in body
    # Must be on by default — operators have to opt out, not opt in.
    # Find the migrations block and assert enabled: true within it.
    start = body.find("migrations:")
    end = body.find("\n\n", start)
    block = body[start:end]
    assert "enabled: true" in block
