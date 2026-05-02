"""Tests for audit-log CSV export — S632."""

from __future__ import annotations

import csv
import io
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from loop_control_plane.audit_events import (
    AuditEvent,
    InMemoryAuditEventStore,
)
from loop_control_plane.audit_export import (
    CSV_HEADER,
    AuditExportFilters,
    export_audit_csv,
    stream_audit_csv,
)


WS = uuid.UUID("11111111-1111-4111-8111-111111111111")
WS_OTHER = uuid.UUID("22222222-2222-4222-8222-222222222222")
BASE = datetime(2027, 6, 15, 12, 0, 0, tzinfo=UTC)


def _evt(
    *,
    i: int,
    actor: str = "auth0|alice",
    action: str = "workspace.create",
    rtype: str = "workspace",
    outcome: str = "success",
    workspace_id: uuid.UUID = WS,
    when: datetime | None = None,
) -> AuditEvent:
    return AuditEvent(
        id=uuid.uuid4(),
        occurred_at=when if when is not None else BASE + timedelta(seconds=i),
        workspace_id=workspace_id,
        actor_sub=actor,
        action=action,
        resource_type=rtype,
        resource_id=f"r-{i}",
        request_id=f"req-{i}",
        payload_hash=f"deadbeef{i:04x}",
        outcome=outcome,
    )


def _parse(csv_body: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_body))
    return list(reader)


def test_header_is_first_line_and_matches_csv_header_constant() -> None:
    store = InMemoryAuditEventStore()
    body = export_audit_csv(store, WS)
    first = body.splitlines()[0]
    assert first.split(",") == list(CSV_HEADER)


def test_round_trip_three_rows_no_filters() -> None:
    store = InMemoryAuditEventStore()
    for i in range(3):
        store.insert(_evt(i=i))
    rows = _parse(export_audit_csv(store, WS))
    assert len(rows) == 3
    assert {r["actor_sub"] for r in rows} == {"auth0|alice"}
    assert {r["outcome"] for r in rows} == {"success"}


def test_filter_by_actor_action_outcome() -> None:
    store = InMemoryAuditEventStore()
    store.insert(_evt(i=0, actor="auth0|alice", outcome="success"))
    store.insert(_evt(i=1, actor="auth0|bob", outcome="success"))
    store.insert(_evt(i=2, actor="auth0|alice", outcome="denied"))
    store.insert(
        _evt(i=3, actor="auth0|alice", action="workspace.delete", outcome="success")
    )
    rows = _parse(
        export_audit_csv(
            store,
            WS,
            AuditExportFilters(
                actor_sub="auth0|alice",
                action="workspace.create",
                outcome="success",
            ),
        )
    )
    assert len(rows) == 1
    assert rows[0]["actor_sub"] == "auth0|alice"
    assert rows[0]["action"] == "workspace.create"
    assert rows[0]["outcome"] == "success"


def test_filter_by_time_window_inclusive_bounds() -> None:
    store = InMemoryAuditEventStore()
    for i in range(10):
        store.insert(_evt(i=i, when=BASE + timedelta(minutes=i)))
    rows = _parse(
        export_audit_csv(
            store,
            WS,
            AuditExportFilters(
                time_from=BASE + timedelta(minutes=3),
                time_to=BASE + timedelta(minutes=6),
            ),
        )
    )
    assert len(rows) == 4  # minutes 3,4,5,6 inclusive


def test_filter_by_resource_type_and_resource_id() -> None:
    store = InMemoryAuditEventStore()
    store.insert(_evt(i=0, rtype="workspace"))
    store.insert(_evt(i=1, rtype="workspace_member"))
    store.insert(_evt(i=2, rtype="workspace_member"))
    rows = _parse(
        export_audit_csv(
            store, WS, AuditExportFilters(resource_type="workspace_member")
        )
    )
    assert len(rows) == 2
    assert {r["resource_type"] for r in rows} == {"workspace_member"}

    rows = _parse(
        export_audit_csv(store, WS, AuditExportFilters(resource_id="r-1"))
    )
    assert len(rows) == 1
    assert rows[0]["resource_id"] == "r-1"


def test_other_workspace_events_excluded() -> None:
    store = InMemoryAuditEventStore()
    store.insert(_evt(i=0, workspace_id=WS))
    store.insert(_evt(i=1, workspace_id=WS_OTHER))
    rows = _parse(export_audit_csv(store, WS))
    assert len(rows) == 1


def test_stream_chunks_have_bounded_row_counts() -> None:
    store = InMemoryAuditEventStore()
    for i in range(2500):
        store.insert(_evt(i=i))
    chunks = list(stream_audit_csv(store, WS, chunk_rows=500))
    # First chunk is header-only; then ceil(2500/500) = 5 data chunks.
    assert len(chunks) == 6
    header_chunk = chunks[0]
    assert header_chunk.startswith("id,")
    # Each data chunk has at most 500 rows (no header counts).
    for c in chunks[1:]:
        assert c.count("\n") <= 500


def test_chunk_rows_must_be_positive() -> None:
    store = InMemoryAuditEventStore()
    with pytest.raises(ValueError):
        next(stream_audit_csv(store, WS, chunk_rows=0))


def test_csv_quotes_commas_in_resource_id() -> None:
    store = InMemoryAuditEventStore()
    e = _evt(i=0)
    # Patch a comma into resource_id via dataclass replace-style construction.
    e2 = AuditEvent(
        id=e.id,
        occurred_at=e.occurred_at,
        workspace_id=e.workspace_id,
        actor_sub=e.actor_sub,
        action=e.action,
        resource_type=e.resource_type,
        resource_id="ws,with,commas",
        request_id=e.request_id,
        payload_hash=e.payload_hash,
        outcome=e.outcome,
    )
    store.insert(e2)
    body = export_audit_csv(store, WS)
    rows = _parse(body)
    assert len(rows) == 1
    assert rows[0]["resource_id"] == "ws,with,commas"


def test_export_100k_rows_under_budget() -> None:
    """AC: filtered export in <30s for ≤100k rows.

    Budget enforced here is 10s — well under the 30s AC — so the test
    catches accidental quadratic behaviour rather than tight CI timing.
    """
    store = InMemoryAuditEventStore()
    n = 100_000
    for i in range(n):
        store.insert(_evt(i=i))

    start = time.perf_counter()
    total_bytes = 0
    row_count = 0
    for chunk in stream_audit_csv(store, WS, chunk_rows=5000):
        total_bytes += len(chunk)
        row_count += chunk.count("\n")
    elapsed = time.perf_counter() - start

    # row_count includes the header line.
    assert row_count == n + 1
    assert total_bytes > 0
    assert elapsed < 10.0, f"100k-row export took {elapsed:.2f}s (budget 10s)"
