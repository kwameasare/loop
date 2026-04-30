"""Trial-conversion email nudges (S331).

Trials run for 14 days. We send three reminder emails:

* ``T+7d`` (i.e. 7 days remaining)
* ``T+13d`` (1 day remaining)
* ``T+14d`` (expired)

Each (workspace_id, kind) is sent at most once. The scheduler is a pure
function of (workspaces, now, already_sent) -> list[Nudge] so it composes
with any cron / temporal driver. Email delivery is delegated to an
``EmailSender`` Protocol (already in the channels package); opt-out is
honoured by the caller's ``opted_out`` set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

TRIAL_LENGTH_DAYS: int = 14


class TrialNudgeKind(StrEnum):
    SEVEN_DAYS_LEFT = "seven_days_left"
    ONE_DAY_LEFT = "one_day_left"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class TrialState:
    """Minimum trial info the scheduler needs."""

    workspace_id: UUID
    started_at: datetime
    converted: bool = False  # paid customers no longer receive nudges

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class TrialNudge:
    """A single nudge to send."""

    workspace_id: UUID
    kind: TrialNudgeKind
    scheduled_for: datetime


@dataclass(slots=True)
class TrialNudgeScheduler:
    """Compute the set of nudges due for a population of trials.

    State is held externally (in the caller's DB); pass ``already_sent``
    on every call so the scheduler stays a pure function.
    """

    trial_length_days: int = TRIAL_LENGTH_DAYS
    opted_out: set[UUID] = field(default_factory=set)

    def due(
        self,
        *,
        trials: list[TrialState],
        now: datetime,
        already_sent: set[tuple[UUID, TrialNudgeKind]],
    ) -> list[TrialNudge]:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        out: list[TrialNudge] = []
        for trial in trials:
            if trial.converted or trial.workspace_id in self.opted_out:
                continue
            for kind, when in self._milestones(trial):
                if when > now:
                    continue
                if (trial.workspace_id, kind) in already_sent:
                    continue
                out.append(
                    TrialNudge(
                        workspace_id=trial.workspace_id,
                        kind=kind,
                        scheduled_for=when,
                    )
                )
        out.sort(key=lambda n: (n.scheduled_for, n.workspace_id.bytes, n.kind.value))
        return out

    def _milestones(self, trial: TrialState) -> list[tuple[TrialNudgeKind, datetime]]:
        ends_at = trial.started_at + timedelta(days=self.trial_length_days)
        return [
            (TrialNudgeKind.SEVEN_DAYS_LEFT, ends_at - timedelta(days=7)),
            (TrialNudgeKind.ONE_DAY_LEFT, ends_at - timedelta(days=1)),
            (TrialNudgeKind.EXPIRED, ends_at),
        ]


def utcnow() -> datetime:
    """Tz-aware now() helper. Centralised so tests can monkey-patch one place."""
    return datetime.now(tz=UTC)


__all__ = [
    "TRIAL_LENGTH_DAYS",
    "TrialNudge",
    "TrialNudgeKind",
    "TrialNudgeScheduler",
    "TrialState",
    "utcnow",
]
