"""Tests for GDPR Art-17 data-deletion workflow — S635."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from loop_control_plane.data_deletion import (
    DataDeletionError,
    DataDeletionState,
    InMemoryDataDeletionJobQueue,
    InMemoryDataDeletionStore,
    RecordingDataDeletionEmailNotifier,
    complete_data_deletion,
    enqueue_data_deletion,
)


WS = uuid.UUID("11111111-1111-4111-8111-111111111111")


def test_enqueue_persists_pending_request_and_enqueues_one_job() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    req = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    assert req.state is DataDeletionState.PENDING
    assert req.workspace_id == WS
    assert len(queue.jobs) == 1
    assert queue.jobs[0].request_id == req.id
    assert queue.jobs[0].workspace_id == WS
    assert list(store.list_for_workspace(WS)) == [req]


def test_enqueue_is_idempotent_while_pending_request_exists() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    first = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    second = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    assert second.id == first.id
    assert len(queue.jobs) == 1  # no duplicate job


def test_enqueue_after_previous_completion_creates_new_request() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    notifier = RecordingDataDeletionEmailNotifier()
    first = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    complete_data_deletion(
        request_id=first.id,
        rows_deleted=42,
        store=store,
        notifier=notifier,
    )
    second = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    assert second.id != first.id
    assert second.state is DataDeletionState.PENDING
    assert len(queue.jobs) == 2


def test_enqueue_rejects_empty_sub_and_bad_email() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    with pytest.raises(DataDeletionError):
        enqueue_data_deletion(
            workspace_id=WS,
            requested_by_sub="   ",
            requested_by_email="alice@example.com",
            store=store,
            job_queue=queue,
        )
    with pytest.raises(DataDeletionError):
        enqueue_data_deletion(
            workspace_id=WS,
            requested_by_sub="auth0|alice",
            requested_by_email="not-an-email",
            store=store,
            job_queue=queue,
        )


def test_complete_marks_completed_records_rows_and_emails_requester() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    notifier = RecordingDataDeletionEmailNotifier()
    req = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    completed_at = datetime.now(UTC) + timedelta(minutes=5)
    out = complete_data_deletion(
        request_id=req.id,
        rows_deleted=12345,
        store=store,
        notifier=notifier,
        now=completed_at,
    )
    assert out.state is DataDeletionState.COMPLETED
    assert out.rows_deleted == 12345
    assert out.completed_at == completed_at
    assert out.failure_reason is None

    assert len(notifier.sent) == 1
    email = notifier.sent[0]
    assert email.to == "alice@example.com"
    assert "completed" in email.subject.lower()
    assert "12345" in email.body
    assert str(req.id) in email.body


def test_complete_failure_records_reason_and_sends_failure_email() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    notifier = RecordingDataDeletionEmailNotifier()
    req = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    out = complete_data_deletion(
        request_id=req.id,
        rows_deleted=0,
        store=store,
        notifier=notifier,
        failure_reason="data-plane unavailable",
    )
    assert out.state is DataDeletionState.FAILED
    assert out.failure_reason == "data-plane unavailable"
    assert len(notifier.sent) == 1
    assert "FAILED" in notifier.sent[0].subject
    assert "data-plane unavailable" in notifier.sent[0].body


def test_cannot_complete_an_already_completed_request() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    notifier = RecordingDataDeletionEmailNotifier()
    req = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    complete_data_deletion(
        request_id=req.id,
        rows_deleted=1,
        store=store,
        notifier=notifier,
    )
    with pytest.raises(DataDeletionError):
        complete_data_deletion(
            request_id=req.id,
            rows_deleted=1,
            store=store,
            notifier=notifier,
        )


def test_complete_unknown_id_raises() -> None:
    store = InMemoryDataDeletionStore()
    notifier = RecordingDataDeletionEmailNotifier()
    with pytest.raises(DataDeletionError):
        complete_data_deletion(
            request_id=uuid.uuid4(),
            rows_deleted=0,
            store=store,
            notifier=notifier,
        )


def test_complete_negative_rows_rejected() -> None:
    store = InMemoryDataDeletionStore()
    queue = InMemoryDataDeletionJobQueue()
    notifier = RecordingDataDeletionEmailNotifier()
    req = enqueue_data_deletion(
        workspace_id=WS,
        requested_by_sub="auth0|alice",
        requested_by_email="alice@example.com",
        store=store,
        job_queue=queue,
    )
    with pytest.raises(DataDeletionError):
        complete_data_deletion(
            request_id=req.id,
            rows_deleted=-1,
            store=store,
            notifier=notifier,
        )
