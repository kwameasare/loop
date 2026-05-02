"""GDPR Art-17 data-deletion requests — S635.

Implements the workflow behind the cp-api endpoint
``POST /v1/workspaces/{id}/data-deletion``:

1. Caller (workspace admin) submits a deletion request with their
   actor sub. The request is persisted in ``data_deletion_requests``
   in state ``pending`` and a job is enqueued onto the deletion
   work queue.
2. The async worker picks up the job, runs the cascade against the
   workspace's tenant data, then calls :func:`complete_data_deletion`
   which transitions the request to ``completed`` (or ``failed``)
   and emits a results email to the requester.

This module is the orchestration layer; the actual table-level
cascade lives in the data-plane and is outside the scope of S635.
The Protocols here are the seams the cp-api wires to Postgres + the
job queue + an email transport in production, while the in-memory
implementations are used by tests.

Public API:

* :class:`DataDeletionRequest` — dataclass for one row.
* :class:`DataDeletionState` — enum of legal states.
* :class:`DataDeletionStore` / :class:`InMemoryDataDeletionStore`.
* :class:`DataDeletionJobQueue` / :class:`InMemoryDataDeletionJobQueue`.
* :class:`DataDeletionEmailNotifier` /
  :class:`RecordingDataDeletionEmailNotifier`.
* :func:`enqueue_data_deletion` — POST handler entry point.
* :func:`complete_data_deletion` — worker entry point.
"""

from __future__ import annotations

import enum
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol

__all__ = [
    "DataDeletionEmailNotifier",
    "DataDeletionError",
    "DataDeletionJob",
    "DataDeletionJobQueue",
    "DataDeletionRequest",
    "DataDeletionState",
    "DataDeletionStore",
    "InMemoryDataDeletionJobQueue",
    "InMemoryDataDeletionStore",
    "RecordingDataDeletionEmailNotifier",
    "complete_data_deletion",
    "enqueue_data_deletion",
]


class DataDeletionState(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class DataDeletionError(ValueError):
    """Raised for invalid input or illegal state transitions."""


@dataclass(frozen=True, slots=True)
class DataDeletionRequest:
    id: uuid.UUID
    workspace_id: uuid.UUID
    requested_by_sub: str
    requested_by_email: str
    requested_at: datetime
    state: DataDeletionState
    completed_at: datetime | None = None
    rows_deleted: int | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DataDeletionJob:
    request_id: uuid.UUID
    workspace_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class _SentEmail:
    to: str
    subject: str
    body: str


class DataDeletionStore(Protocol):
    def insert(self, request: DataDeletionRequest) -> None: ...
    def get(self, request_id: uuid.UUID) -> DataDeletionRequest: ...
    def update(self, request: DataDeletionRequest) -> None: ...
    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> Iterable[DataDeletionRequest]: ...


class DataDeletionJobQueue(Protocol):
    def enqueue(self, job: DataDeletionJob) -> None: ...


class DataDeletionEmailNotifier(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class InMemoryDataDeletionStore:
    def __init__(self) -> None:
        self._rows: dict[uuid.UUID, DataDeletionRequest] = {}

    def insert(self, request: DataDeletionRequest) -> None:
        if request.id in self._rows:
            raise DataDeletionError(f"duplicate request id: {request.id}")
        self._rows[request.id] = request

    def get(self, request_id: uuid.UUID) -> DataDeletionRequest:
        if request_id not in self._rows:
            raise DataDeletionError(f"unknown request id: {request_id}")
        return self._rows[request_id]

    def update(self, request: DataDeletionRequest) -> None:
        if request.id not in self._rows:
            raise DataDeletionError(f"unknown request id: {request.id}")
        self._rows[request.id] = request

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[DataDeletionRequest]:
        return sorted(
            (r for r in self._rows.values() if r.workspace_id == workspace_id),
            key=lambda r: r.requested_at,
        )


class InMemoryDataDeletionJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DataDeletionJob] = []

    def enqueue(self, job: DataDeletionJob) -> None:
        self.jobs.append(job)


class RecordingDataDeletionEmailNotifier:
    def __init__(self) -> None:
        self.sent: list[_SentEmail] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append(_SentEmail(to=to, subject=subject, body=body))


def _validate_email(email: str) -> str:
    email = email.strip()
    if not email or "@" not in email:
        raise DataDeletionError("requested_by_email must be a non-empty email")
    return email


def enqueue_data_deletion(
    *,
    workspace_id: uuid.UUID,
    requested_by_sub: str,
    requested_by_email: str,
    store: DataDeletionStore,
    job_queue: DataDeletionJobQueue,
    now: datetime | None = None,
) -> DataDeletionRequest:
    """POST handler: persist a pending request and enqueue the job.

    Idempotency: if the workspace already has a ``pending`` request,
    the existing one is returned unchanged and no new job is enqueued.
    """
    if not requested_by_sub.strip():
        raise DataDeletionError("requested_by_sub must not be empty")
    email = _validate_email(requested_by_email)
    now = now or datetime.now(UTC)

    existing = [
        r
        for r in store.list_for_workspace(workspace_id)
        if r.state is DataDeletionState.PENDING
    ]
    if existing:
        return existing[0]

    request = DataDeletionRequest(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        requested_by_sub=requested_by_sub.strip(),
        requested_by_email=email,
        requested_at=now,
        state=DataDeletionState.PENDING,
    )
    store.insert(request)
    job_queue.enqueue(
        DataDeletionJob(request_id=request.id, workspace_id=workspace_id)
    )
    return request


def complete_data_deletion(
    *,
    request_id: uuid.UUID,
    rows_deleted: int,
    store: DataDeletionStore,
    notifier: DataDeletionEmailNotifier,
    failure_reason: str | None = None,
    now: datetime | None = None,
) -> DataDeletionRequest:
    """Worker entry point: transition pending → completed (or failed)
    and email the requester with the results."""
    if rows_deleted < 0:
        raise DataDeletionError("rows_deleted must be >= 0")
    request = store.get(request_id)
    if request.state is not DataDeletionState.PENDING:
        raise DataDeletionError(
            f"request {request_id} is in state {request.state.value}; "
            "only pending requests may be completed"
        )
    now = now or datetime.now(UTC)

    if failure_reason is not None:
        updated = replace(
            request,
            state=DataDeletionState.FAILED,
            completed_at=now,
            failure_reason=failure_reason,
            rows_deleted=rows_deleted,
        )
        subject = "Loop: data-deletion request FAILED"
        body = (
            f"Hi,\n\nYour data-deletion request {request.id} for workspace "
            f"{request.workspace_id} could not be completed.\n\n"
            f"Reason: {failure_reason}\n\n"
            f"Rows deleted before failure: {rows_deleted}\n\n"
            "Loop Support will follow up shortly. — Loop"
        )
    else:
        updated = replace(
            request,
            state=DataDeletionState.COMPLETED,
            completed_at=now,
            rows_deleted=rows_deleted,
        )
        subject = "Loop: data-deletion request completed"
        body = (
            f"Hi,\n\nYour GDPR Art-17 data-deletion request {request.id} for "
            f"workspace {request.workspace_id} has completed.\n\n"
            f"Rows deleted: {rows_deleted}\n"
            f"Completed at: {now.isoformat()}\n\n"
            "If you did not initiate this request, contact Loop Support "
            "immediately. — Loop"
        )

    store.update(updated)
    notifier.send(to=request.requested_by_email, subject=subject, body=body)
    return updated
