"""Data-retention policy enforcement — S807.

Implements a scheduled-job model that deletes data records exceeding their
retention window, audits each deletion batch, and surfaces the policy
configuration for the user-facing documentation page.

Design
------
:class:`RetentionPolicy` describes the maximum age (in days) for each
``DataClass``.  The defaults mirror the values in SECURITY.md §11.1:

    * ``CONVERSATION`` -- 365 days (customer-configurable 1d-7y)
    * ``TRACE`` -- 90 days (customer-configurable 7d-1y)
    * ``VOICE_RECORDING`` — 30 days (opt-in only)
    * ``KB_DOCUMENT`` — no expiry (customer-deletes explicitly)
    * ``AUDIT_LOG`` — 2555 days (7 years; not customer-configurable)
    * ``BACKUP`` — 14 days standard (90 days enterprise)

:class:`RetentionJob` is the scheduler entry-point.  It calls
:class:`DataStore` (a Protocol) to list and delete expired records, then
calls :class:`AuditSink` (a Protocol) to record each deletion batch.
In-memory stubs are provided for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

__all__ = [
    "DataClass",
    "DataRecord",
    "DataStore",
    "DeletionBatch",
    "InMemoryAuditSink",
    "InMemoryDataStore",
    "RetentionError",
    "RetentionJob",
    "RetentionPolicy",
]


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class DataClass(StrEnum):
    """Categories of data subject to retention policy."""

    CONVERSATION = "conversation"
    TRACE = "trace"
    VOICE_RECORDING = "voice_recording"
    KB_DOCUMENT = "kb_document"
    AUDIT_LOG = "audit_log"
    BACKUP = "backup"


@dataclass(frozen=True, slots=True)
class DataRecord:
    """A single data record managed by the retention job.

    Args:
        id: Opaque record identifier.
        workspace_id: Owning workspace.
        data_class: Category the record belongs to.
        region: Deployment region (e.g. ``"us-east-1"``).
        created_at: Creation timestamp used for age calculation.
    """

    id: UUID
    workspace_id: UUID
    data_class: DataClass
    region: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DeletionBatch:
    """Result of one retention-job run.

    Args:
        data_class: Which class of data was swept.
        region: Region swept.
        deleted_count: How many records were deleted.
        oldest_deleted_at: Oldest ``created_at`` among deleted records.
        job_run_at: When the job ran.
    """

    data_class: DataClass
    region: str
    deleted_count: int
    oldest_deleted_at: datetime | None
    job_run_at: datetime


class RetentionError(RuntimeError):
    """Raised when the retention job cannot complete."""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class DataStore(Protocol):
    """Seam for the storage layer queried and mutated by :class:`RetentionJob`."""

    def list_older_than(
        self,
        *,
        data_class: DataClass,
        region: str,
        cutoff: datetime,
    ) -> list[DataRecord]:
        """Return records of *data_class* in *region* created before *cutoff*."""
        ...

    def delete_batch(self, record_ids: list[UUID]) -> int:
        """Delete records by ID.  Returns the count actually deleted."""
        ...


class AuditSink(Protocol):
    """Receives deletion audit events from :class:`RetentionJob`."""

    def record_batch(self, batch: DeletionBatch) -> None:
        """Persist the deletion batch for compliance audit trails."""
        ...


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

# Sentinel: no expiry — records are kept until explicitly deleted by the user.
_NO_EXPIRY = -1


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Maximum retention window per :class:`DataClass` (days).

    A value of ``-1`` means the data class has no time-based expiry and
    records are only removed on explicit customer deletion.

    Args:
        windows: Dict mapping DataClass to days.  Any class not present
            inherits the default (see class-level defaults below).
        no_expiry_classes: DataClass values explicitly exempted from
            time-based deletion; overrides *windows* if both are set.
    """

    windows: dict[DataClass, int] = field(
        default_factory=lambda: {
            DataClass.CONVERSATION: 365,
            DataClass.TRACE: 90,
            DataClass.VOICE_RECORDING: 30,
            DataClass.KB_DOCUMENT: _NO_EXPIRY,
            DataClass.AUDIT_LOG: 365 * 7,  # 7 years
            DataClass.BACKUP: 14,
        }
    )

    def retention_days(self, data_class: DataClass) -> int:
        """Return the configured retention window, or *_NO_EXPIRY* if none."""
        return self.windows.get(data_class, _NO_EXPIRY)

    def has_expiry(self, data_class: DataClass) -> bool:
        return self.retention_days(data_class) != _NO_EXPIRY

    def cutoff_for(self, data_class: DataClass, *, now: datetime) -> datetime | None:
        """Return the cutoff datetime for *data_class*, or ``None`` if no expiry."""
        days = self.retention_days(data_class)
        if days == _NO_EXPIRY:
            return None
        return now - timedelta(days=days)


# ---------------------------------------------------------------------------
# Retention job
# ---------------------------------------------------------------------------


class RetentionJob:
    """Scheduled job that enforces the data-retention policy.

    For each (data_class, region) combination it:
    1. Queries the :class:`DataStore` for records older than the configured
       retention window.
    2. Deletes them in a single batch.
    3. Records the deletion in the :class:`AuditSink`.

    Usage::

        job = RetentionJob(
            store=my_data_store,
            audit=my_audit_sink,
            policy=RetentionPolicy(),
            regions=["us-east-1", "eu-west-1"],
        )
        batches = job.run()
    """

    def __init__(
        self,
        *,
        store: DataStore,
        audit: AuditSink,
        policy: RetentionPolicy | None = None,
        regions: list[str],
    ) -> None:
        self._store = store
        self._audit = audit
        self._policy = policy or RetentionPolicy()
        self._regions = list(regions)

    def run(self, *, now: datetime | None = None) -> list[DeletionBatch]:
        """Run the retention sweep.  Returns one :class:`DeletionBatch` per
        (data_class, region) pair where at least some records were found."""
        if now is None:
            now = datetime.now(UTC)

        batches: list[DeletionBatch] = []

        for data_class in DataClass:
            if not self._policy.has_expiry(data_class):
                continue
            cutoff = self._policy.cutoff_for(data_class, now=now)
            assert cutoff is not None  # guaranteed by has_expiry

            for region in self._regions:
                expired = self._store.list_older_than(
                    data_class=data_class,
                    region=region,
                    cutoff=cutoff,
                )
                if not expired:
                    continue

                ids = [r.id for r in expired]
                deleted = self._store.delete_batch(ids)
                oldest = min(r.created_at for r in expired)

                batch = DeletionBatch(
                    data_class=data_class,
                    region=region,
                    deleted_count=deleted,
                    oldest_deleted_at=oldest,
                    job_run_at=now,
                )
                self._audit.record_batch(batch)
                batches.append(batch)

        return batches


# ---------------------------------------------------------------------------
# In-memory fakes for testing
# ---------------------------------------------------------------------------


class InMemoryDataStore:
    """In-memory implementation of :class:`DataStore` for tests."""

    def __init__(self) -> None:
        self._records: dict[UUID, DataRecord] = {}

    def insert(self, record: DataRecord) -> None:
        self._records[record.id] = record

    def list_older_than(
        self,
        *,
        data_class: DataClass,
        region: str,
        cutoff: datetime,
    ) -> list[DataRecord]:
        return [
            r
            for r in self._records.values()
            if r.data_class is data_class and r.region == region and r.created_at < cutoff
        ]

    def delete_batch(self, record_ids: list[UUID]) -> int:
        count = 0
        for rid in record_ids:
            if rid in self._records:
                del self._records[rid]
                count += 1
        return count

    def count(self) -> int:
        return len(self._records)


class InMemoryAuditSink:
    """Records deletion batches in memory for test assertions."""

    def __init__(self) -> None:
        self.batches: list[DeletionBatch] = []

    def record_batch(self, batch: DeletionBatch) -> None:
        self.batches.append(batch)
