"""Workspace eval-suite registry (P0.4).

cp-api hosts the suite metadata + run history; eval-harness owns the
actual evaluator logic + dataset content. The studio's "Evals" tab
lists suites, lets the operator kick off a run, and displays
historical results.

Suite shape: a name + a frozen dataset reference + a list of metric
names (e.g. ["faithfulness", "groundedness"]). Runs are immutable
once recorded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EvalRunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvalSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=128)
    dataset_ref: str = Field(min_length=1, max_length=512)
    metrics: tuple[str, ...] = ()
    created_at: datetime
    created_by: str = Field(min_length=1)


class EvalSuiteCreate(BaseModel):
    """Body for POST /v1/workspaces/{id}/eval-suites."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    dataset_ref: str = Field(min_length=1, max_length=512)
    metrics: list[str] = Field(default_factory=list)


class EvalRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    suite_id: UUID
    workspace_id: UUID
    state: EvalRunState
    metrics: dict[str, float] = Field(default_factory=dict)
    triggered_by: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None


class EvalRunStart(BaseModel):
    """Body for POST /v1/eval-suites/{id}/runs."""

    model_config = ConfigDict(extra="forbid")
    note: str = Field(default="", max_length=1024)


class EvalError(ValueError):
    """Raised on duplicates / unknown ids / invalid transitions."""


class EvalSuiteService:
    """In-memory store for suite metadata + run history. Production
    wires Postgres-backed persistence + a queue for the eval-harness
    worker."""

    def __init__(self) -> None:
        self._suites: dict[UUID, EvalSuite] = {}
        self._runs: dict[UUID, EvalRun] = {}
        self._lock = asyncio.Lock()

    async def list_suites(self, workspace_id: UUID) -> list[EvalSuite]:
        async with self._lock:
            rows = [s for s in self._suites.values() if s.workspace_id == workspace_id]
            rows.sort(key=lambda s: s.created_at, reverse=True)
            return rows

    async def get_suite(
        self, *, workspace_id: UUID, suite_id: UUID
    ) -> EvalSuite:
        async with self._lock:
            suite = self._suites.get(suite_id)
            if suite is None or suite.workspace_id != workspace_id:
                raise EvalError(f"unknown suite: {suite_id}")
            return suite

    async def create_suite(
        self,
        *,
        workspace_id: UUID,
        body: EvalSuiteCreate,
        actor_sub: str,
    ) -> EvalSuite:
        async with self._lock:
            existing = next(
                (
                    s
                    for s in self._suites.values()
                    if s.workspace_id == workspace_id and s.name == body.name
                ),
                None,
            )
            if existing is not None:
                raise EvalError(
                    f"suite name already taken in this workspace: {body.name}"
                )
            suite = EvalSuite(
                id=uuid4(),
                workspace_id=workspace_id,
                name=body.name,
                dataset_ref=body.dataset_ref,
                metrics=tuple(body.metrics),
                created_at=datetime.now(UTC),
                created_by=actor_sub,
            )
            self._suites[suite.id] = suite
            return suite

    async def start_run(
        self,
        *,
        workspace_id: UUID,
        suite_id: UUID,
        actor_sub: str,
    ) -> EvalRun:
        async with self._lock:
            suite = self._suites.get(suite_id)
            if suite is None or suite.workspace_id != workspace_id:
                raise EvalError(f"unknown suite: {suite_id}")
            run = EvalRun(
                id=uuid4(),
                suite_id=suite_id,
                workspace_id=workspace_id,
                state=EvalRunState.PENDING,
                triggered_by=actor_sub,
                started_at=datetime.now(UTC),
            )
            self._runs[run.id] = run
            return run

    async def list_runs(
        self, *, workspace_id: UUID, suite_id: UUID
    ) -> list[EvalRun]:
        async with self._lock:
            suite = self._suites.get(suite_id)
            if suite is None or suite.workspace_id != workspace_id:
                raise EvalError(f"unknown suite: {suite_id}")
            rows = [r for r in self._runs.values() if r.suite_id == suite_id]
            rows.sort(key=lambda r: r.started_at, reverse=True)
            return rows


def serialise_suite(s: EvalSuite) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "workspace_id": str(s.workspace_id),
        "name": s.name,
        "dataset_ref": s.dataset_ref,
        "metrics": list(s.metrics),
        "created_at": s.created_at.isoformat(),
        "created_by": s.created_by,
    }


def serialise_run(r: EvalRun) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "suite_id": str(r.suite_id),
        "workspace_id": str(r.workspace_id),
        "state": r.state.value,
        "metrics": r.metrics,
        "triggered_by": r.triggered_by,
        "started_at": r.started_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "failure_reason": r.failure_reason,
    }


__all__ = [
    "EvalError",
    "EvalRun",
    "EvalRunStart",
    "EvalRunState",
    "EvalSuite",
    "EvalSuiteCreate",
    "EvalSuiteService",
    "serialise_run",
    "serialise_suite",
]
