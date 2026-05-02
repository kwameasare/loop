"""Tests for retention.py — S807: data-retention policy enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from loop_control_plane.retention import (
    DataClass,
    DataRecord,
    InMemoryAuditSink,
    InMemoryDataStore,
    RetentionJob,
    RetentionPolicy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    data_class: DataClass,
    region: str = "us-east-1",
    age_days: int = 0,
) -> DataRecord:
    return DataRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        data_class=data_class,
        region=region,
        created_at=datetime.now(UTC) - timedelta(days=age_days),
    )


def _job(store: InMemoryDataStore, audit: InMemoryAuditSink) -> RetentionJob:
    return RetentionJob(
        store=store,
        audit=audit,
        policy=RetentionPolicy(),
        regions=["us-east-1"],
    )


NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------


def test_policy_default_windows_are_set() -> None:
    policy = RetentionPolicy()
    assert policy.retention_days(DataClass.CONVERSATION) == 365
    assert policy.retention_days(DataClass.TRACE) == 90
    assert policy.retention_days(DataClass.VOICE_RECORDING) == 30
    assert policy.retention_days(DataClass.KB_DOCUMENT) == -1
    assert policy.retention_days(DataClass.AUDIT_LOG) == 365 * 7
    assert policy.retention_days(DataClass.BACKUP) == 14


def test_policy_kb_document_has_no_expiry() -> None:
    policy = RetentionPolicy()
    assert not policy.has_expiry(DataClass.KB_DOCUMENT)


def test_policy_conversation_has_expiry() -> None:
    policy = RetentionPolicy()
    assert policy.has_expiry(DataClass.CONVERSATION)


def test_policy_cutoff_for_conversation() -> None:
    policy = RetentionPolicy()
    cutoff = policy.cutoff_for(DataClass.CONVERSATION, now=NOW)
    assert cutoff == NOW - timedelta(days=365)


def test_policy_cutoff_for_no_expiry_class_returns_none() -> None:
    policy = RetentionPolicy()
    assert policy.cutoff_for(DataClass.KB_DOCUMENT, now=NOW) is None


def test_policy_custom_window_overrides_default() -> None:
    policy = RetentionPolicy(windows={DataClass.CONVERSATION: 30})
    assert policy.retention_days(DataClass.CONVERSATION) == 30


# ---------------------------------------------------------------------------
# RetentionJob
# ---------------------------------------------------------------------------


def test_job_deletes_expired_conversation_records() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    # 400-day-old record → should be deleted (> 365)
    old = _record(DataClass.CONVERSATION, age_days=400)
    # 10-day-old record → should be kept
    fresh = _record(DataClass.CONVERSATION, age_days=10)
    store.insert(old)
    store.insert(fresh)

    job = _job(store, audit)
    batches = job.run()

    assert store.count() == 1, "fresh record must survive"
    assert any(b.data_class is DataClass.CONVERSATION for b in batches)
    conv_batch = next(b for b in batches if b.data_class is DataClass.CONVERSATION)
    assert conv_batch.deleted_count == 1


def test_job_does_not_delete_kb_documents() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    # Very old KB document — must NOT be deleted by retention job
    store.insert(_record(DataClass.KB_DOCUMENT, age_days=9999))

    job = _job(store, audit)
    job.run()

    assert store.count() == 1


def test_job_records_audit_batch_for_each_deletion() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    store.insert(_record(DataClass.TRACE, age_days=200))  # > 90 days
    store.insert(_record(DataClass.TRACE, age_days=100))  # > 90 days

    _job(store, audit).run()

    trace_batches = [b for b in audit.batches if b.data_class is DataClass.TRACE]
    assert len(trace_batches) == 1
    assert trace_batches[0].deleted_count == 2


def test_job_audit_batch_contains_oldest_deleted_at() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    older = _record(DataClass.BACKUP, age_days=20)  # > 14 days
    newer = _record(DataClass.BACKUP, age_days=15)  # > 14 days
    store.insert(older)
    store.insert(newer)

    _job(store, audit).run()

    batch = next(b for b in audit.batches if b.data_class is DataClass.BACKUP)
    assert batch.oldest_deleted_at == older.created_at


def test_job_skips_regions_not_configured() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    # Record in eu-west-1 — job only runs for us-east-1
    store.insert(
        DataRecord(
            id=uuid4(),
            workspace_id=uuid4(),
            data_class=DataClass.TRACE,
            region="eu-west-1",
            created_at=datetime.now(UTC) - timedelta(days=365),
        )
    )

    job = RetentionJob(
        store=store,
        audit=audit,
        policy=RetentionPolicy(),
        regions=["us-east-1"],
    )
    job.run()

    assert store.count() == 1, "eu-west-1 record must not be touched"


def test_job_returns_batches_only_for_non_empty_deletions() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    # No expired records at all
    store.insert(_record(DataClass.CONVERSATION, age_days=1))

    batches = _job(store, audit).run()

    assert batches == []
    assert audit.batches == []


def test_job_multiple_data_classes_deleted_independently() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    store.insert(_record(DataClass.CONVERSATION, age_days=400))
    store.insert(_record(DataClass.TRACE, age_days=200))

    batches = _job(store, audit).run()

    classes = {b.data_class for b in batches}
    assert DataClass.CONVERSATION in classes
    assert DataClass.TRACE in classes


def test_job_uses_default_policy_when_none_provided() -> None:
    store = InMemoryDataStore()
    audit = InMemoryAuditSink()

    store.insert(_record(DataClass.VOICE_RECORDING, age_days=60))  # > 30 days

    job = RetentionJob(store=store, audit=audit, regions=["us-east-1"])
    batches = job.run()

    assert any(b.data_class is DataClass.VOICE_RECORDING for b in batches)


# ---------------------------------------------------------------------------
# Docs page
# ---------------------------------------------------------------------------


def test_data_retention_docs_page_exists() -> None:
    import pathlib

    path = pathlib.Path("docs/site/data-retention.md")
    assert path.exists(), "docs/site/data-retention.md must exist"


def test_data_retention_docs_page_covers_all_data_classes() -> None:
    import pathlib

    content = pathlib.Path("docs/site/data-retention.md").read_text()
    for label in ("Conversation", "Trace", "Voice", "Knowledge", "Audit", "Backup"):
        assert label.lower() in content.lower(), f"{label!r} missing from data-retention.md"


def test_data_retention_docs_page_mentions_audit_trail() -> None:
    import pathlib

    content = pathlib.Path("docs/site/data-retention.md").read_text()
    assert "audit" in content.lower()
