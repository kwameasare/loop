"""Encrypted backup verification -- S808.

Implements the weekly backup-restore-then-diff job described in S808.

Design
------
:class:`BackupManifest`
    Metadata record for a stored backup: id, created_at, region, checksum.

:class:`BackupStore` (Protocol)
    Seam to the real object-store that holds encrypted backup archives.
    ``latest()`` returns the newest manifest; ``restore_to_scratch(manifest)``
    restores the archive to an isolated scratch environment and returns a
    :class:`RestoredSnapshot`.

:class:`LiveDataSource` (Protocol)
    Seam to the live database/object-store.  ``snapshot()`` returns a
    :class:`RestoredSnapshot` representing the current data state.

:class:`RestoredSnapshot`
    A lightweight snapshot: a mapping of record keys to their content hashes.

:class:`DiffReport`
    The output of :func:`diff_snapshots`: lists keys that are only in the
    live snapshot (``only_in_live``), only in the backup
    (``only_in_backup``), and keys present in both but whose hashes differ
    (``content_mismatch``).  A report where all three lists are empty is a
    clean verify.

:class:`AlertSink` (Protocol)
    Receives a :class:`DiffReport` when the diff is non-empty.

:class:`BackupVerificationJob`
    Orchestrates the weekly flow:
    1. Fetch latest backup manifest from :class:`BackupStore`.
    2. Restore it to scratch.
    3. Snapshot the live source.
    4. Diff the two snapshots.
    5. If the diff is non-empty, call :class:`AlertSink`.
    6. Return the :class:`VerificationResult`.

In-memory stubs are provided for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

__all__ = [
    "AlertSink",
    "BackupManifest",
    "BackupStore",
    "BackupVerificationError",
    "BackupVerificationJob",
    "DiffReport",
    "InMemoryAlertSink",
    "InMemoryBackupStore",
    "InMemoryLiveDataSource",
    "LiveDataSource",
    "RestoredSnapshot",
    "VerificationResult",
    "diff_snapshots",
]


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Metadata for a single backup archive.

    Args:
        id: Unique backup identifier.
        created_at: When the backup was taken.
        region: Region where the backup is stored.
        checksum: SHA-256 hex digest of the encrypted archive.
    """

    id: UUID
    created_at: datetime
    region: str
    checksum: str


@dataclass(frozen=True, slots=True)
class RestoredSnapshot:
    """Snapshot of data: mapping of record key to content hash.

    Args:
        source_label: Human-readable label (``"live"`` or ``"backup"``).
        records: Dict mapping opaque key -> SHA-256 content hash.
    """

    source_label: str
    records: dict[str, str]


@dataclass(frozen=True, slots=True)
class DiffReport:
    """Result of comparing a backup snapshot against live data.

    Args:
        backup_id: The manifest ID that was restored.
        only_in_live: Keys present in live but absent from backup.
        only_in_backup: Keys present in backup but absent from live.
        content_mismatch: Keys in both snapshots whose content hashes differ.
        verified_at: Timestamp of the diff.
    """

    backup_id: UUID
    only_in_live: list[str]
    only_in_backup: list[str]
    content_mismatch: list[str]
    verified_at: datetime

    @property
    def is_clean(self) -> bool:
        return not (self.only_in_live or self.only_in_backup or self.content_mismatch)


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Output of one :class:`BackupVerificationJob` run.

    Args:
        manifest: The backup that was verified.
        report: The diff report produced.
        alerted: Whether the :class:`AlertSink` was called.
    """

    manifest: BackupManifest
    report: DiffReport
    alerted: bool


class BackupVerificationError(RuntimeError):
    """Raised when the verification job cannot proceed."""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class BackupStore(Protocol):
    """Seam to the object store that holds encrypted backup archives."""

    def latest(self, *, region: str) -> BackupManifest | None:
        """Return the most recent backup manifest for *region*, or ``None``."""
        ...

    def restore_to_scratch(self, manifest: BackupManifest) -> RestoredSnapshot:
        """Decrypt and restore *manifest* to an isolated scratch environment."""
        ...


class LiveDataSource(Protocol):
    """Seam to the live data for comparison."""

    def snapshot(self, *, region: str) -> RestoredSnapshot:
        """Return a current snapshot of live data in *region*."""
        ...


class AlertSink(Protocol):
    """Receives diff-mismatch alerts from :class:`BackupVerificationJob`."""

    def alert(self, report: DiffReport) -> None:
        """Send an alert for a non-clean diff report."""
        ...


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def diff_snapshots(
    *,
    backup: RestoredSnapshot,
    live: RestoredSnapshot,
    backup_id: UUID,
    now: datetime,
) -> DiffReport:
    """Compare *backup* and *live* snapshots; return a :class:`DiffReport`."""
    backup_keys = set(backup.records)
    live_keys = set(live.records)

    only_in_live = sorted(live_keys - backup_keys)
    only_in_backup = sorted(backup_keys - live_keys)
    content_mismatch = sorted(
        k for k in backup_keys & live_keys if backup.records[k] != live.records[k]
    )

    return DiffReport(
        backup_id=backup_id,
        only_in_live=only_in_live,
        only_in_backup=only_in_backup,
        content_mismatch=content_mismatch,
        verified_at=now,
    )


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------


class BackupVerificationJob:
    """Weekly job that restores the latest backup and diffs it against live.

    Usage::

        job = BackupVerificationJob(
            backup_store=my_store,
            live_source=my_db,
            alert_sink=my_pagerduty,
            region="us-east-1",
        )
        result = job.run()
        assert result.report.is_clean
    """

    def __init__(
        self,
        *,
        backup_store: BackupStore,
        live_source: LiveDataSource,
        alert_sink: AlertSink,
        region: str,
    ) -> None:
        self._backup_store = backup_store
        self._live_source = live_source
        self._alert_sink = alert_sink
        self._region = region

    def run(self, *, now: datetime | None = None) -> VerificationResult:
        """Execute the restore-then-diff verification.

        Raises:
            BackupVerificationError: if no backup exists for the configured region.
        """
        if now is None:
            now = datetime.now(UTC)

        manifest = self._backup_store.latest(region=self._region)
        if manifest is None:
            raise BackupVerificationError(f"No backup found for region {self._region!r}")

        backup_snapshot = self._backup_store.restore_to_scratch(manifest)
        live_snapshot = self._live_source.snapshot(region=self._region)

        report = diff_snapshots(
            backup=backup_snapshot,
            live=live_snapshot,
            backup_id=manifest.id,
            now=now,
        )

        alerted = False
        if not report.is_clean:
            self._alert_sink.alert(report)
            alerted = True

        return VerificationResult(manifest=manifest, report=report, alerted=alerted)


# ---------------------------------------------------------------------------
# In-memory fakes for tests
# ---------------------------------------------------------------------------


class InMemoryBackupStore:
    """In-memory implementation of :class:`BackupStore` for tests."""

    def __init__(self) -> None:
        self._manifests: list[BackupManifest] = []
        # snapshot keyed by manifest.id
        self._snapshots: dict[UUID, RestoredSnapshot] = {}

    def add(self, manifest: BackupManifest, snapshot: RestoredSnapshot) -> None:
        self._manifests.append(manifest)
        self._snapshots[manifest.id] = snapshot

    def latest(self, *, region: str) -> BackupManifest | None:
        regional = [m for m in self._manifests if m.region == region]
        if not regional:
            return None
        return max(regional, key=lambda m: m.created_at)

    def restore_to_scratch(self, manifest: BackupManifest) -> RestoredSnapshot:
        return self._snapshots[manifest.id]


class InMemoryLiveDataSource:
    """In-memory implementation of :class:`LiveDataSource` for tests."""

    def __init__(self, records: dict[str, str] | None = None) -> None:
        self._records: dict[str, str] = records or {}

    def snapshot(self, *, region: str) -> RestoredSnapshot:
        return RestoredSnapshot(source_label="live", records=dict(self._records))


class InMemoryAlertSink:
    """Captures alerts in memory for test assertions."""

    def __init__(self) -> None:
        self.alerts: list[DiffReport] = []

    def alert(self, report: DiffReport) -> None:
        self.alerts.append(report)
