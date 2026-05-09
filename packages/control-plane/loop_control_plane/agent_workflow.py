from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

BranchStatus = Literal["active", "staged", "merged", "abandoned"]
ChangeSetStatus = Literal[
    "draft",
    "ready_for_tests",
    "ready_for_review",
    "converted_to_release_candidate",
    "abandoned",
]
ReleaseCandidateStatus = Literal[
    "draft",
    "testing",
    "blocked",
    "ready_for_approval",
    "approved",
    "deployable",
    "superseded",
]
GateStatus = Literal["pending", "passed", "failed"]


class BranchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    base_version_id: str = Field(default="production", max_length=160)


class BranchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    agent_id: UUID
    name: str
    base_version_id: str
    created_by_user_id: str
    status: BranchStatus
    created_at: datetime
    updated_at: datetime


class ChangeSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=1200)
    source_type: str = Field(default="manual_edit", max_length=120)
    source_refs: list[str] = Field(default_factory=list, max_length=50)
    changed_objects: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class ChangeSetTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_results_ref: str = Field(min_length=1, max_length=240)
    required_eval_suites: list[str] = Field(default_factory=list, max_length=25)
    passed: bool = True


class ChangeSetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    agent_id: UUID
    branch_id: str
    name: str
    summary: str
    source_type: str
    source_refs: list[str]
    changed_objects: list[dict[str, Any]]
    status: ChangeSetStatus
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime
    eval_results_ref: str | None = None
    required_eval_suites: list[str] = Field(default_factory=list)


class ReleaseCandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_eval_suites: list[str] = Field(default_factory=list, max_length=25)
    required_approvals: list[str] = Field(
        default_factory=lambda: ["owner", "compliance"],
        max_length=25,
    )


class ReleaseCandidateGateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str = Field(min_length=1, max_length=120)
    status: GateStatus
    evidence_ref: str = Field(default="", max_length=240)
    message: str = Field(default="", max_length=500)


class ReleaseCandidateApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1, max_length=120)
    comment: str = Field(default="", max_length=1200)


class ReleaseCandidateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    agent_id: UUID
    branch_id: str
    change_set_id: str
    candidate_version_id: str
    readiness: list[dict[str, Any]]
    required_eval_suites: list[str]
    required_approvals: list[dict[str, Any]]
    status: ReleaseCandidateStatus
    created_at: datetime
    updated_at: datetime


def branch_payload(record: BranchRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def change_set_payload(record: ChangeSetRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def release_candidate_payload(record: ReleaseCandidateRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def workflow_payload(
    *,
    branches: list[BranchRecord],
    change_sets: list[ChangeSetRecord],
    release_candidates: list[ReleaseCandidateRecord],
) -> dict[str, Any]:
    return {
        "branches": [branch_payload(item) for item in branches],
        "change_sets": [change_set_payload(item) for item in change_sets],
        "release_candidates": [release_candidate_payload(item) for item in release_candidates],
    }


class AgentWorkflowRegistry:
    def __init__(self) -> None:
        self._branches: dict[UUID, list[BranchRecord]] = {}
        self._change_sets: dict[UUID, list[ChangeSetRecord]] = {}
        self._release_candidates: dict[UUID, list[ReleaseCandidateRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(
        self,
        *,
        agent: AgentRecord,
    ) -> tuple[list[BranchRecord], list[ChangeSetRecord], list[ReleaseCandidateRecord]]:
        async with self._lock:
            return (
                list(self._branches.get(agent.id, [])),
                list(self._change_sets.get(agent.id, [])),
                list(self._release_candidates.get(agent.id, [])),
            )

    async def create_branch(
        self,
        *,
        agent: AgentRecord,
        body: BranchCreate,
        actor_sub: str,
    ) -> BranchRecord:
        async with self._lock:
            now = datetime.now(UTC)
            record = BranchRecord(
                id=f"br_{uuid4().hex[:12]}",
                agent_id=agent.id,
                name=body.name,
                base_version_id=body.base_version_id,
                created_by_user_id=actor_sub,
                status="active",
                created_at=now,
                updated_at=now,
            )
            self._branches.setdefault(agent.id, []).insert(0, record)
            return record

    async def create_change_set(
        self,
        *,
        agent: AgentRecord,
        body: ChangeSetCreate,
        actor_sub: str,
    ) -> ChangeSetRecord:
        async with self._lock:
            if body.branch_id not in {item.id for item in self._branches.get(agent.id, [])}:
                raise WorkspaceError(f"unknown branch: {body.branch_id}")
            now = datetime.now(UTC)
            record = ChangeSetRecord(
                id=f"cs_{uuid4().hex[:12]}",
                agent_id=agent.id,
                branch_id=body.branch_id,
                name=body.name,
                summary=body.summary,
                source_type=body.source_type,
                source_refs=body.source_refs,
                changed_objects=body.changed_objects,
                status="draft",
                created_by_user_id=actor_sub,
                created_at=now,
                updated_at=now,
            )
            self._change_sets.setdefault(agent.id, []).insert(0, record)
            return record

    async def mark_ready_for_tests(
        self,
        *,
        agent: AgentRecord,
        change_set_id: str,
    ) -> ChangeSetRecord:
        async with self._lock:
            return self._update_change_set_status(
                agent=agent,
                change_set_id=change_set_id,
                allowed={"draft"},
                status="ready_for_tests",
            )

    async def mark_ready_for_review(
        self,
        *,
        agent: AgentRecord,
        change_set_id: str,
        body: ChangeSetTestResult,
    ) -> ChangeSetRecord:
        async with self._lock:
            if not body.passed:
                raise WorkspaceError("required tests must pass before review")
            record = self._update_change_set_status(
                agent=agent,
                change_set_id=change_set_id,
                allowed={"ready_for_tests"},
                status="ready_for_review",
            )
            updated = record.model_copy(
                update={
                    "eval_results_ref": body.eval_results_ref,
                    "required_eval_suites": body.required_eval_suites,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._replace_change_set(agent=agent, record=updated)
            return updated

    async def create_release_candidate(
        self,
        *,
        agent: AgentRecord,
        change_set_id: str,
        candidate_version_id: str,
        body: ReleaseCandidateCreate,
    ) -> ReleaseCandidateRecord:
        async with self._lock:
            change_set = self._find_change_set(agent=agent, change_set_id=change_set_id)
            if change_set.status != "ready_for_review":
                raise WorkspaceError("change set must be ready_for_review")
            required_eval_suites = body.required_eval_suites or change_set.required_eval_suites
            readiness = [
                {
                    "id": f"eval:{suite}",
                    "label": f"Eval suite {suite}",
                    "status": "passed",
                    "evidence_ref": change_set.eval_results_ref,
                    "message": "Required eval suite passed before release candidate creation.",
                }
                for suite in required_eval_suites
            ]
            if not readiness:
                readiness = [
                    {
                        "id": "eval:required",
                        "label": "Required eval coverage",
                        "status": "pending",
                        "evidence_ref": "",
                        "message": "Attach required eval suite evidence.",
                    }
                ]
            required_approvals = [
                {
                    "id": approval_id,
                    "state": "requested",
                    "satisfied": False,
                    "comment": "",
                    "decided_at": None,
                }
                for approval_id in body.required_approvals
            ]
            now = datetime.now(UTC)
            status: ReleaseCandidateStatus = (
                "ready_for_approval"
                if readiness and all(item["status"] == "passed" for item in readiness)
                else "testing"
            )
            record = ReleaseCandidateRecord(
                id=f"rc_{uuid4().hex[:12]}",
                agent_id=agent.id,
                branch_id=change_set.branch_id,
                change_set_id=change_set.id,
                candidate_version_id=candidate_version_id,
                readiness=readiness,
                required_eval_suites=required_eval_suites,
                required_approvals=required_approvals,
                status=status,
                created_at=now,
                updated_at=now,
            )
            self._release_candidates.setdefault(agent.id, []).insert(0, record)
            self._replace_change_set(
                agent=agent,
                record=change_set.model_copy(
                    update={
                        "status": "converted_to_release_candidate",
                        "updated_at": now,
                    }
                ),
            )
            return record

    async def update_gate(
        self,
        *,
        agent: AgentRecord,
        release_candidate_id: str,
        body: ReleaseCandidateGateUpdate,
    ) -> ReleaseCandidateRecord:
        async with self._lock:
            record = self._find_release_candidate(
                agent=agent,
                release_candidate_id=release_candidate_id,
            )
            found = False
            readiness: list[dict[str, Any]] = []
            for gate in record.readiness:
                if gate.get("id") == body.gate_id:
                    found = True
                    readiness.append(
                        {
                            **gate,
                            "status": body.status,
                            "evidence_ref": body.evidence_ref,
                            "message": body.message,
                        }
                    )
                else:
                    readiness.append(gate)
            if not found:
                readiness.append(
                    {
                        "id": body.gate_id,
                        "label": body.gate_id,
                        "status": body.status,
                        "evidence_ref": body.evidence_ref,
                        "message": body.message,
                    }
                )
            status: ReleaseCandidateStatus = "testing"
            if any(item.get("status") == "failed" for item in readiness):
                status = "blocked"
            elif readiness and all(item.get("status") == "passed" for item in readiness):
                status = "ready_for_approval"
            updated = record.model_copy(
                update={
                    "readiness": readiness,
                    "status": status,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._replace_release_candidate(agent=agent, record=updated)
            return updated

    async def approve(
        self,
        *,
        agent: AgentRecord,
        release_candidate_id: str,
        body: ReleaseCandidateApproval,
        actor_sub: str,
    ) -> ReleaseCandidateRecord:
        async with self._lock:
            record = self._find_release_candidate(
                agent=agent,
                release_candidate_id=release_candidate_id,
            )
            if any(item.get("status") == "failed" for item in record.readiness):
                raise WorkspaceError("failed readiness gates block approval")
            approvals: list[dict[str, Any]] = []
            found = False
            now = datetime.now(UTC)
            for approval in record.required_approvals:
                if approval.get("id") == body.approval_id:
                    found = True
                    approvals.append(
                        {
                            **approval,
                            "state": "approved",
                            "satisfied": True,
                            "actor_sub": actor_sub,
                            "comment": body.comment,
                            "decided_at": now.isoformat(),
                        }
                    )
                else:
                    approvals.append(approval)
            if not found:
                raise WorkspaceError(f"unknown approval: {body.approval_id}")
            status: ReleaseCandidateStatus = (
                "deployable"
                if approvals and all(item.get("satisfied") for item in approvals)
                else "approved"
            )
            updated = record.model_copy(
                update={
                    "required_approvals": approvals,
                    "status": status,
                    "updated_at": now,
                }
            )
            self._replace_release_candidate(agent=agent, record=updated)
            return updated

    def _find_change_set(
        self,
        *,
        agent: AgentRecord,
        change_set_id: str,
    ) -> ChangeSetRecord:
        for record in self._change_sets.get(agent.id, []):
            if record.id == change_set_id:
                return record
        raise WorkspaceError(f"unknown change set: {change_set_id}")

    def _find_release_candidate(
        self,
        *,
        agent: AgentRecord,
        release_candidate_id: str,
    ) -> ReleaseCandidateRecord:
        for record in self._release_candidates.get(agent.id, []):
            if record.id == release_candidate_id:
                return record
        raise WorkspaceError(f"unknown release candidate: {release_candidate_id}")

    def _replace_change_set(
        self,
        *,
        agent: AgentRecord,
        record: ChangeSetRecord,
    ) -> None:
        items = self._change_sets.get(agent.id, [])
        for index, item in enumerate(items):
            if item.id == record.id:
                items[index] = record
                return
        raise WorkspaceError(f"unknown change set: {record.id}")

    def _replace_release_candidate(
        self,
        *,
        agent: AgentRecord,
        record: ReleaseCandidateRecord,
    ) -> None:
        items = self._release_candidates.get(agent.id, [])
        for index, item in enumerate(items):
            if item.id == record.id:
                items[index] = record
                return
        raise WorkspaceError(f"unknown release candidate: {record.id}")

    def _update_change_set_status(
        self,
        *,
        agent: AgentRecord,
        change_set_id: str,
        allowed: set[ChangeSetStatus],
        status: ChangeSetStatus,
    ) -> ChangeSetRecord:
        record = self._find_change_set(agent=agent, change_set_id=change_set_id)
        if record.status not in allowed:
            raise WorkspaceError(
                f"change set {change_set_id} cannot move from {record.status} to {status}"
            )
        updated = record.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
        self._replace_change_set(agent=agent, record=updated)
        return updated
