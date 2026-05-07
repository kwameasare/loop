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
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EvalRunState(StrEnum):
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


class EvalCaseCreate(BaseModel):
    """Body for adding one eval case to a suite."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=256)
    input: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    scorers: list[dict[str, Any]] = Field(default_factory=list)
    source: str = Field(default="manual", max_length=128)
    source_ref: str = Field(default="", max_length=512)
    attachments: list[str] = Field(default_factory=list)


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    suite_id: UUID
    workspace_id: UUID
    name: str
    input: dict[str, Any]
    expected: dict[str, Any]
    scorers: tuple[dict[str, Any], ...]
    source: str
    source_ref: str
    attachments: tuple[str, ...]
    created_at: datetime
    created_by: str


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
        self._cases: dict[UUID, EvalCase] = {}
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

    async def get_or_create_suite(
        self,
        *,
        workspace_id: UUID,
        name: str,
        dataset_ref: str,
        metrics: list[str],
        actor_sub: str,
    ) -> EvalSuite:
        async with self._lock:
            existing = next(
                (
                    suite
                    for suite in self._suites.values()
                    if suite.workspace_id == workspace_id and suite.name == name
                ),
                None,
            )
            if existing is not None:
                return existing
            suite = EvalSuite(
                id=uuid4(),
                workspace_id=workspace_id,
                name=name,
                dataset_ref=dataset_ref,
                metrics=tuple(metrics),
                created_at=datetime.now(UTC),
                created_by=actor_sub,
            )
            self._suites[suite.id] = suite
            return suite

    async def add_case(
        self,
        *,
        workspace_id: UUID,
        suite_id: UUID,
        body: EvalCaseCreate,
        actor_sub: str,
    ) -> EvalCase:
        async with self._lock:
            suite = self._suites.get(suite_id)
            if suite is None or suite.workspace_id != workspace_id:
                raise EvalError(f"unknown suite: {suite_id}")
            case = EvalCase(
                id=uuid4(),
                suite_id=suite_id,
                workspace_id=workspace_id,
                name=body.name,
                input=body.input,
                expected=body.expected,
                scorers=tuple(body.scorers),
                source=body.source,
                source_ref=body.source_ref,
                attachments=tuple(body.attachments),
                created_at=datetime.now(UTC),
                created_by=actor_sub,
            )
            self._cases[case.id] = case
            return case

    async def list_cases(
        self, *, workspace_id: UUID, suite_id: UUID
    ) -> list[EvalCase]:
        async with self._lock:
            suite = self._suites.get(suite_id)
            if suite is None or suite.workspace_id != workspace_id:
                raise EvalError(f"unknown suite: {suite_id}")
            rows = [case for case in self._cases.values() if case.suite_id == suite_id]
            rows.sort(key=lambda case: case.created_at, reverse=True)
            return rows

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


def serialise_case(c: EvalCase) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "suite_id": str(c.suite_id),
        "workspace_id": str(c.workspace_id),
        "name": c.name,
        "input": c.input,
        "expected": c.expected,
        "scorers": list(c.scorers),
        "source": c.source,
        "source_ref": c.source_ref,
        "attachments": list(c.attachments),
        "created_at": c.created_at.isoformat(),
        "created_by": c.created_by,
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
    "EvalCase",
    "EvalCaseCreate",
    "EvalError",
    "EvalRun",
    "EvalRunStart",
    "EvalRunState",
    "EvalSuite",
    "EvalSuiteCreate",
    "EvalSuiteService",
    "serialise_case",
    "serialise_run",
    "serialise_suite",
]
