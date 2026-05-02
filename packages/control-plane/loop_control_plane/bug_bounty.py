"""Bug-bounty triage model -- S809.

Provides domain types and a simple in-memory tracker for managing the
first-three-reports SLA gate required by S809.

This is *not* a HackerOne client library; it is the internal triage state
machine used to validate that:

1. Every inbound report is acknowledged within 24 hours.
2. A triage decision is reached within 5 business days.
3. The program can be considered *live* once three reports have been
   triaged and closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

__all__ = [
    "BountyProgram",
    "BountyReport",
    "ReportDecision",
    "ReportSeverity",
    "SLAViolation",
    "TriageError",
]

# SLA constants
_ACK_SLA_HOURS = 24
_TRIAGE_SLA_BUSINESS_DAYS = 5
# Approximate: 5 business days ~ 7 calendar days (conservative)
_TRIAGE_SLA_CALENDAR_DAYS = 7


class ReportSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ReportDecision(StrEnum):
    VALID = "valid"
    DUPLICATE = "duplicate"
    OUT_OF_SCOPE = "out_of_scope"
    INFORMATIONAL = "informational"
    NA = "n/a"


@dataclass(slots=True)
class BountyReport:
    """Represents one HackerOne report in the internal triage system.

    Args:
        id: Internal UUID (maps to HackerOne report ID externally).
        hackerone_id: HackerOne report reference string.
        submitted_at: When the researcher submitted the report.
        acknowledged_at: When the team first acknowledged it (or None).
        decided_at: When the triage decision was reached (or None).
        decision: The triage outcome (or None if pending).
        severity: Estimated severity (or None if not yet assessed).
    """

    id: UUID
    hackerone_id: str
    submitted_at: datetime
    acknowledged_at: datetime | None = None
    decided_at: datetime | None = None
    decision: ReportDecision | None = None
    severity: ReportSeverity | None = None

    @property
    def is_acknowledged(self) -> bool:
        return self.acknowledged_at is not None

    @property
    def is_decided(self) -> bool:
        return self.decided_at is not None and self.decision is not None

    def ack_sla_met(self) -> bool | None:
        """Return True if ack was within SLA, False if violated, None if pending."""
        if self.acknowledged_at is None:
            return None
        delta = self.acknowledged_at - self.submitted_at
        return delta <= timedelta(hours=_ACK_SLA_HOURS)

    def triage_sla_met(self) -> bool | None:
        """Return True if triage was within SLA, False if violated, None if pending."""
        if self.decided_at is None:
            return None
        delta = self.decided_at - self.submitted_at
        return delta <= timedelta(days=_TRIAGE_SLA_CALENDAR_DAYS)


@dataclass(frozen=True, slots=True)
class SLAViolation:
    """Records an SLA breach for a report.

    Args:
        report_id: The report that breached SLA.
        stage: ``"ack"`` or ``"triage"``.
        elapsed: How long the stage took.
        sla_limit: The allowed duration.
    """

    report_id: UUID
    stage: str
    elapsed: timedelta
    sla_limit: timedelta


class TriageError(RuntimeError):
    """Raised when an invalid triage transition is attempted."""


class BountyProgram:
    """In-memory bug-bounty triage tracker.

    Tracks the lifecycle of submitted reports:
    submitted -> acknowledged -> decided (valid/duplicate/n-a/oos).

    The program is considered *live* once at least three reports have been
    triaged (decided) with their SLAs met.

    Usage::

        program = BountyProgram()
        rid = program.submit("H1-001", submitted_at=now)
        program.acknowledge(rid, acked_at=now + timedelta(hours=2))
        program.decide(rid, decision=ReportDecision.VALID,
                       severity=ReportSeverity.HIGH, decided_at=...)
        assert program.is_live
    """

    def __init__(self) -> None:
        self._reports: dict[UUID, BountyReport] = {}

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def submit(self, hackerone_id: str, *, submitted_at: datetime) -> UUID:
        """Register a new inbound report.  Returns the internal UUID."""
        from uuid import uuid4

        rid = uuid4()
        self._reports[rid] = BountyReport(
            id=rid,
            hackerone_id=hackerone_id,
            submitted_at=submitted_at,
        )
        return rid

    def acknowledge(self, report_id: UUID, *, acked_at: datetime) -> None:
        """Record first acknowledgement of *report_id*."""
        report = self._get(report_id)
        if report.is_acknowledged:
            raise TriageError(f"Report {report_id} already acknowledged")
        report.acknowledged_at = acked_at

    def decide(
        self,
        report_id: UUID,
        *,
        decision: ReportDecision,
        decided_at: datetime,
        severity: ReportSeverity | None = None,
    ) -> None:
        """Record the triage decision for *report_id*."""
        report = self._get(report_id)
        if not report.is_acknowledged:
            raise TriageError(f"Report {report_id} must be acknowledged before a decision")
        if report.is_decided:
            raise TriageError(f"Report {report_id} already has a decision")
        report.decision = decision
        report.decided_at = decided_at
        if severity is not None:
            report.severity = severity

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def report(self, report_id: UUID) -> BountyReport:
        return self._get(report_id)

    def all_reports(self) -> list[BountyReport]:
        return list(self._reports.values())

    @property
    def is_live(self) -> bool:
        """True once three reports have been decided with SLAs met."""
        triaged_clean = [
            r
            for r in self._reports.values()
            if r.is_decided and r.ack_sla_met() is True and r.triage_sla_met() is True
        ]
        return len(triaged_clean) >= 3

    def sla_violations(self) -> list[SLAViolation]:
        """Return all SLA violations across all reports."""
        violations: list[SLAViolation] = []
        for r in self._reports.values():
            if r.ack_sla_met() is False and r.acknowledged_at is not None:
                violations.append(
                    SLAViolation(
                        report_id=r.id,
                        stage="ack",
                        elapsed=r.acknowledged_at - r.submitted_at,
                        sla_limit=timedelta(hours=_ACK_SLA_HOURS),
                    )
                )
            if r.triage_sla_met() is False and r.decided_at is not None:
                violations.append(
                    SLAViolation(
                        report_id=r.id,
                        stage="triage",
                        elapsed=r.decided_at - r.submitted_at,
                        sla_limit=timedelta(days=_TRIAGE_SLA_CALENDAR_DAYS),
                    )
                )
        return violations

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _get(self, report_id: UUID) -> BountyReport:
        try:
            return self._reports[report_id]
        except KeyError:
            raise TriageError(f"Unknown report {report_id}") from None
