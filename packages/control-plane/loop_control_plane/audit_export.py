"""Audit-log CSV export — S632.

AC: filtered CSV export in <30s for ≤100k rows.

The export is a generator-driven streaming writer over the standard
library's :mod:`csv` module. It accepts a filter object identical
to the cp-api query API (actor, action, resource_type, resource_id,
ip — currently unmodelled in :class:`AuditEvent` so handled as an
ignore-by-default key — time window, outcome) and streams rows in
chunks so that memory usage stays O(chunk_size) regardless of total
row count.

Performance budget:

* 100,000 rows must serialise in well under 30 seconds on commodity
  hardware. The included ``test_export_100k_rows_under_budget`` test
  enforces a generous 10-second ceiling against the in-memory store
  to give plenty of headroom over the 30-second AC.

Public API:

* :class:`AuditExportFilters` — filter object (all fields optional).
* :func:`stream_audit_csv` — yields CSV-formatted ``str`` lines.
* :func:`export_audit_csv` — convenience wrapper that returns a single
  ``str`` (suitable for small exports / unit tests).
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .audit_events import AuditEvent

__all__ = [
    "AuditExportFilters",
    "AuditExportSource",
    "CSV_HEADER",
    "export_audit_csv",
    "stream_audit_csv",
]


CSV_HEADER: tuple[str, ...] = (
    "id",
    "occurred_at",
    "workspace_id",
    "actor_sub",
    "action",
    "resource_type",
    "resource_id",
    "request_id",
    "payload_hash",
    "outcome",
)


@dataclass(frozen=True, slots=True)
class AuditExportFilters:
    """All fields are optional. Empty filters export every row in scope."""

    actor_sub: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
    outcome: str | None = None  # 'success' | 'denied' | 'error'


class AuditExportSource(Protocol):
    """Read-only seam over the audit store. Production wires this to
    a streaming Postgres cursor against ``audit_events``."""

    def list_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> Iterable[AuditEvent]: ...


def _matches(event: AuditEvent, f: AuditExportFilters) -> bool:
    if f.actor_sub is not None and event.actor_sub != f.actor_sub:
        return False
    if f.action is not None and event.action != f.action:
        return False
    if f.resource_type is not None and event.resource_type != f.resource_type:
        return False
    if f.resource_id is not None and event.resource_id != f.resource_id:
        return False
    if f.outcome is not None and event.outcome != f.outcome:
        return False
    if f.time_from is not None and event.occurred_at < f.time_from:
        return False
    if f.time_to is not None and event.occurred_at > f.time_to:
        return False
    return True


def _row(event: AuditEvent) -> tuple[str, ...]:
    return (
        str(event.id),
        event.occurred_at.isoformat(),
        str(event.workspace_id),
        event.actor_sub,
        event.action,
        event.resource_type,
        event.resource_id or "",
        event.request_id or "",
        event.payload_hash or "",
        event.outcome,
    )


def stream_audit_csv(
    source: AuditExportSource,
    workspace_id: uuid.UUID,
    filters: AuditExportFilters | None = None,
    *,
    chunk_rows: int = 1000,
) -> Iterator[str]:
    """Yield CSV-formatted lines (incl. header) for streaming responses.

    Each yielded chunk contains up to ``chunk_rows`` rows. Memory stays
    bounded at O(chunk_rows) regardless of how many events match.
    """
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be >= 1")
    f = filters or AuditExportFilters()

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate()

    rows_in_chunk = 0
    for event in source.list_for_workspace(workspace_id):
        if not _matches(event, f):
            continue
        writer.writerow(_row(event))
        rows_in_chunk += 1
        if rows_in_chunk >= chunk_rows:
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
            rows_in_chunk = 0

    if rows_in_chunk > 0:
        yield buf.getvalue()


def export_audit_csv(
    source: AuditExportSource,
    workspace_id: uuid.UUID,
    filters: AuditExportFilters | None = None,
) -> str:
    """Return the full CSV body as a string. Intended for small exports
    and unit tests; production HTTP handlers use :func:`stream_audit_csv`
    directly."""
    return "".join(stream_audit_csv(source, workspace_id, filters))
