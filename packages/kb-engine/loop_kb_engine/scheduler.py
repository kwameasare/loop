"""
S494: Scheduled KB refresh — per-doc cron cadence + on-demand trigger.

RefreshScheduler keeps track of refresh configuration and execution history
per document.  It is intentionally pure-Python / no I/O so it can be tested
fast and wired to any event loop or cron framework by the caller.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RefreshStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


@dataclass
class DocRefreshConfig:
    """Refresh configuration for a single document."""

    document_id: UUID
    # Cadence in seconds.  None means no scheduled refresh (manual only).
    interval_seconds: int | None = None
    # Human-readable label for the studio UI, e.g. "every 24 h".
    label: str = "manual"


@dataclass
class DocRefreshRecord:
    """Runtime status for a document's refresh lifecycle."""

    document_id: UUID
    status: RefreshStatus = RefreshStatus.PENDING
    last_run_at: float | None = None  # Unix timestamp
    next_run_at: float | None = None  # Unix timestamp; None if no schedule
    error: str | None = None
    run_count: int = 0


# Callable type: async or sync ingest coroutine — scheduler just calls it.
IngestFn = Callable[[UUID], None]


class RefreshScheduler:
    """
    Pure-state scheduler: no threads, no asyncio.  The caller drives ticks.

    Typical usage
    -------------
    scheduler = RefreshScheduler(ingest_fn=my_ingest)
    scheduler.configure(DocRefreshConfig(doc_id, interval_seconds=86400))
    # ... on cron tick:
    scheduler.tick()
    # ... on user demand:
    scheduler.trigger(doc_id)
    """

    def __init__(self, ingest_fn: IngestFn, *, clock: Callable[[], float] = time.time) -> None:
        self._ingest = ingest_fn
        self._clock = clock
        self._configs: dict[UUID, DocRefreshConfig] = {}
        self._records: dict[UUID, DocRefreshRecord] = {}

    # ---------------------------------------------------------------- configure

    def configure(self, config: DocRefreshConfig) -> None:
        """Register or update the refresh config for a document."""
        self._configs[config.document_id] = config
        if config.document_id not in self._records:
            now = self._clock()
            next_run = (
                now + config.interval_seconds
                if config.interval_seconds is not None
                else None
            )
            self._records[config.document_id] = DocRefreshRecord(
                document_id=config.document_id,
                next_run_at=next_run,
            )
        else:
            rec = self._records[config.document_id]
            if config.interval_seconds is not None and rec.next_run_at is None:
                rec.next_run_at = self._clock() + config.interval_seconds

    # ---------------------------------------------------------------- trigger

    def trigger(self, document_id: UUID) -> None:
        """Force an immediate refresh for *document_id* regardless of schedule."""
        self._run(document_id)

    # ---------------------------------------------------------------- tick

    def tick(self) -> list[UUID]:
        """
        Examine all configured documents.  For each whose ``next_run_at`` is
        in the past, run a refresh.

        Returns the list of document IDs that were refreshed this tick.
        """
        now = self._clock()
        refreshed: list[UUID] = []
        for doc_id, rec in self._records.items():
            if rec.next_run_at is not None and now >= rec.next_run_at:
                self._run(doc_id)
                refreshed.append(doc_id)
        return refreshed

    # ---------------------------------------------------------------- status

    def status(self, document_id: UUID) -> DocRefreshRecord | None:
        return self._records.get(document_id)

    def all_statuses(self) -> list[DocRefreshRecord]:
        return list(self._records.values())

    # ---------------------------------------------------------------- private

    def _run(self, document_id: UUID) -> None:
        cfg = self._configs.get(document_id)
        rec = self._records.setdefault(
            document_id,
            DocRefreshRecord(document_id=document_id),
        )
        rec.status = RefreshStatus.RUNNING
        now = self._clock()
        try:
            self._ingest(document_id)
            rec.status = RefreshStatus.OK
            rec.error = None
        except Exception as exc:
            rec.status = RefreshStatus.ERROR
            rec.error = str(exc)
        finally:
            rec.last_run_at = now
            rec.run_count += 1
            if cfg is not None and cfg.interval_seconds is not None:
                rec.next_run_at = now + cfg.interval_seconds
            else:
                rec.next_run_at = None
