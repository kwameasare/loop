"""Tests for backup_verifier.py -- S808: encrypted backup verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from loop_control_plane.backup_verifier import (
    BackupManifest,
    BackupVerificationError,
    BackupVerificationJob,
    DiffReport,
    InMemoryAlertSink,
    InMemoryBackupStore,
    InMemoryLiveDataSource,
    RestoredSnapshot,
    diff_snapshots,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
REGION = "us-east-1"


def _manifest(region: str = REGION, age_days: int = 0) -> BackupManifest:
    return BackupManifest(
        id=uuid4(),
        created_at=NOW - timedelta(days=age_days),
        region=region,
        checksum="abc123",
    )


def _snapshot(records: dict[str, str], label: str = "backup") -> RestoredSnapshot:
    return RestoredSnapshot(source_label=label, records=records)


def _job(
    store: InMemoryBackupStore,
    live: InMemoryLiveDataSource,
    alert: InMemoryAlertSink,
) -> BackupVerificationJob:
    return BackupVerificationJob(
        backup_store=store,
        live_source=live,
        alert_sink=alert,
        region=REGION,
    )


# ---------------------------------------------------------------------------
# diff_snapshots
# ---------------------------------------------------------------------------


def test_diff_identical_snapshots_is_clean() -> None:
    records = {"k1": "hash1", "k2": "hash2"}
    backup = _snapshot(records)
    live = _snapshot(records, label="live")
    mid = uuid4()
    report = diff_snapshots(backup=backup, live=live, backup_id=mid, now=NOW)
    assert report.is_clean
    assert report.backup_id == mid


def test_diff_detects_key_only_in_live() -> None:
    backup = _snapshot({"k1": "h1"})
    live = _snapshot({"k1": "h1", "k2": "h2"}, label="live")
    report = diff_snapshots(backup=backup, live=live, backup_id=uuid4(), now=NOW)
    assert report.only_in_live == ["k2"]
    assert not report.is_clean


def test_diff_detects_key_only_in_backup() -> None:
    backup = _snapshot({"k1": "h1", "k2": "h2"})
    live = _snapshot({"k1": "h1"}, label="live")
    report = diff_snapshots(backup=backup, live=live, backup_id=uuid4(), now=NOW)
    assert report.only_in_backup == ["k2"]
    assert not report.is_clean


def test_diff_detects_content_mismatch() -> None:
    backup = _snapshot({"k1": "old_hash"})
    live = _snapshot({"k1": "new_hash"}, label="live")
    report = diff_snapshots(backup=backup, live=live, backup_id=uuid4(), now=NOW)
    assert report.content_mismatch == ["k1"]
    assert not report.is_clean


# ---------------------------------------------------------------------------
# BackupVerificationJob
# ---------------------------------------------------------------------------


def test_job_returns_clean_result_when_snapshots_match() -> None:
    records = {"key:1": "hash_a", "key:2": "hash_b"}
    manifest = _manifest()
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot(records))
    live = InMemoryLiveDataSource(records)
    alert = InMemoryAlertSink()

    result = _job(store, live, alert).run(now=NOW)

    assert result.report.is_clean
    assert not result.alerted
    assert alert.alerts == []


def test_job_selects_latest_manifest_for_region() -> None:
    older = _manifest(age_days=7)
    newer = _manifest(age_days=1)
    records = {"k": "v"}
    store = InMemoryBackupStore()
    store.add(older, _snapshot(records))
    store.add(newer, _snapshot(records))
    live = InMemoryLiveDataSource(records)
    alert = InMemoryAlertSink()

    result = _job(store, live, alert).run(now=NOW)

    assert result.manifest.id == newer.id


def test_job_alerts_on_mismatch() -> None:
    manifest = _manifest()
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot({"k": "backup_hash"}))
    live = InMemoryLiveDataSource({"k": "live_hash"})
    alert = InMemoryAlertSink()

    result = _job(store, live, alert).run(now=NOW)

    assert not result.report.is_clean
    assert result.alerted
    assert len(alert.alerts) == 1
    assert alert.alerts[0].content_mismatch == ["k"]


def test_job_raises_when_no_backup_exists() -> None:
    store = InMemoryBackupStore()
    live = InMemoryLiveDataSource({})
    alert = InMemoryAlertSink()

    with pytest.raises(BackupVerificationError, match="No backup found"):
        _job(store, live, alert).run(now=NOW)


def test_job_ignores_backups_in_other_regions() -> None:
    manifest = _manifest(region="eu-west-1")
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot({"k": "v"}))
    live = InMemoryLiveDataSource({"k": "v"})
    alert = InMemoryAlertSink()

    with pytest.raises(BackupVerificationError):
        _job(store, live, alert).run(now=NOW)


def test_job_does_not_alert_on_clean_diff() -> None:
    manifest = _manifest()
    records = {"k1": "h1"}
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot(records))
    live = InMemoryLiveDataSource(records)
    alert = InMemoryAlertSink()

    _job(store, live, alert).run(now=NOW)

    assert alert.alerts == []


def test_job_result_contains_manifest_and_report() -> None:
    manifest = _manifest()
    records = {"x": "y"}
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot(records))
    live = InMemoryLiveDataSource(records)
    alert = InMemoryAlertSink()

    result = _job(store, live, alert).run(now=NOW)

    assert result.manifest is manifest
    assert isinstance(result.report, DiffReport)


def test_job_alert_report_has_correct_backup_id() -> None:
    manifest = _manifest()
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot({"k": "a"}))
    live = InMemoryLiveDataSource({"k": "b"})
    alert = InMemoryAlertSink()

    _job(store, live, alert).run(now=NOW)

    assert alert.alerts[0].backup_id == manifest.id


def test_job_alert_includes_verified_at_timestamp() -> None:
    manifest = _manifest()
    store = InMemoryBackupStore()
    store.add(manifest, _snapshot({"k": "a"}))
    live = InMemoryLiveDataSource({"k": "b"})
    alert = InMemoryAlertSink()

    _job(store, live, alert).run(now=NOW)

    assert alert.alerts[0].verified_at == NOW
