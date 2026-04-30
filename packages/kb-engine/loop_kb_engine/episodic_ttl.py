"""Episodic TTL + decay (S493).

Two policies live here:

* **TTL prune** — episodes older than ``ttl_days`` are soft-deleted
  (payload flagged + vector re-zeroed) and hard-deleted after a
  grace period.
* **Salience extension** -- episodes with high salience get extra
  life: ``effective_ttl = ttl_days x salience_multiplier``.

Both run as a nightly job; the implementation is pure-functional so
the job runner is just a thin loop.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

DEFAULT_TTL_DAYS = 90
DEFAULT_HARD_DELETE_GRACE_DAYS = 30
DEFAULT_SALIENCE_MULTIPLIER = 2.0  # high-salience episodes live 2x as long
DEFAULT_HIGH_SALIENCE_THRESHOLD = 0.75


class TtlError(ValueError):
    """TTL config rejected."""


@dataclass(frozen=True, slots=True)
class TtlPolicy:
    ttl_days: int = DEFAULT_TTL_DAYS
    hard_delete_grace_days: int = DEFAULT_HARD_DELETE_GRACE_DAYS
    soft_delete: bool = True
    salience_multiplier: float = DEFAULT_SALIENCE_MULTIPLIER
    high_salience_threshold: float = DEFAULT_HIGH_SALIENCE_THRESHOLD

    def __post_init__(self) -> None:
        if self.ttl_days < 1:
            raise TtlError("ttl_days must be >=1")
        if self.hard_delete_grace_days < 0:
            raise TtlError("hard_delete_grace_days must be >=0")
        if self.salience_multiplier < 1.0:
            raise TtlError("salience_multiplier must be >=1.0")
        if not (0.0 <= self.high_salience_threshold <= 1.0):
            raise TtlError("high_salience_threshold must be in [0,1]")


@dataclass(frozen=True, slots=True)
class EpisodeAgeRecord:
    """Inputs the prune planner needs per episode."""

    point_id: str
    occurred_at_ms: int
    salience: float
    soft_deleted: bool

    def __post_init__(self) -> None:
        if not (0.0 <= self.salience <= 1.0):
            raise TtlError(f"salience must be in [0,1] (got {self.salience})")


@dataclass(frozen=True, slots=True)
class PruneAction:
    point_id: str
    action: str  # "soft_delete" | "hard_delete" | "keep"


@dataclass(frozen=True, slots=True)
class PruneResult:
    soft_deleted: tuple[str, ...]
    hard_deleted: tuple[str, ...]
    kept: tuple[str, ...]


def effective_ttl_ms(salience: float, policy: TtlPolicy) -> int:
    """Compute the per-episode TTL in milliseconds."""
    base = policy.ttl_days * 24 * 60 * 60 * 1000
    if salience >= policy.high_salience_threshold:
        return int(base * policy.salience_multiplier)
    return base


def plan_prune(
    *,
    episodes: Sequence[EpisodeAgeRecord],
    now_ms: int,
    policy: TtlPolicy,
) -> PruneResult:
    """Decide soft / hard / keep for each episode."""
    soft: list[str] = []
    hard: list[str] = []
    keep: list[str] = []
    grace_ms = policy.hard_delete_grace_days * 24 * 60 * 60 * 1000
    for ep in episodes:
        age = now_ms - ep.occurred_at_ms
        ttl_ms = effective_ttl_ms(ep.salience, policy)
        if ep.soft_deleted:
            if age > ttl_ms + grace_ms:
                hard.append(ep.point_id)
            else:
                keep.append(ep.point_id)
        elif age > ttl_ms:
            if policy.soft_delete:
                soft.append(ep.point_id)
            else:
                hard.append(ep.point_id)
        else:
            keep.append(ep.point_id)
    return PruneResult(
        soft_deleted=tuple(soft),
        hard_deleted=tuple(hard),
        kept=tuple(keep),
    )


@runtime_checkable
class EpisodicWriter(Protocol):
    async def soft_delete(self, *, agent_id: str, point_ids: Sequence[str]) -> None: ...

    async def hard_delete(self, *, agent_id: str, point_ids: Sequence[str]) -> None: ...


async def execute_prune(
    *,
    writer: EpisodicWriter,
    agent_id: str,
    plan: PruneResult,
) -> None:
    """Apply a prune plan via the writer."""
    if plan.soft_deleted:
        await writer.soft_delete(agent_id=agent_id, point_ids=plan.soft_deleted)
    if plan.hard_deleted:
        await writer.hard_delete(agent_id=agent_id, point_ids=plan.hard_deleted)


__all__ = [
    "DEFAULT_HARD_DELETE_GRACE_DAYS",
    "DEFAULT_HIGH_SALIENCE_THRESHOLD",
    "DEFAULT_SALIENCE_MULTIPLIER",
    "DEFAULT_TTL_DAYS",
    "EpisodeAgeRecord",
    "EpisodicWriter",
    "PruneAction",
    "PruneResult",
    "TtlError",
    "TtlPolicy",
    "effective_ttl_ms",
    "execute_prune",
    "plan_prune",
]
