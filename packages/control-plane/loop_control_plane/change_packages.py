from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.agent_commitments import CommitmentDocumentRecord
from loop_control_plane.workspaces import WorkspaceError


class ChangePackageGenerate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: str = Field(default="main/draft", max_length=160)
    change_set_id: str = Field(default="manual-change-set", max_length=160)
    release_candidate_id: str = Field(default="rc-current", max_length=160)
    from_version_id: str = Field(default="production", max_length=160)
    to_version_id: str = Field(default="draft", max_length=160)
    target_environment: str = Field(default="production", max_length=64)
    summary: str = Field(default="", max_length=2000)
    semantic_diff: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    eval_results_ref: str = Field(default="evals/not-run", max_length=240)
    replay_results_ref: str = Field(default="replay/not-run", max_length=240)
    risk_summary: str = Field(default="", max_length=1200)
    cost_summary: str = Field(default="", max_length=800)
    latency_summary: str = Field(default="", max_length=800)
    channel_readiness_summary: str = Field(default="", max_length=1200)
    tool_changes: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    memory_changes: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    knowledge_changes: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    rollback_target_version_id: str = Field(default="last-known-safe", max_length=160)


class ChangePackageApprovalAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(max_length=120)
    decision: Literal["approve", "reject", "request_changes", "revoke"] = "approve"
    comment: str = Field(default="", max_length=1200)


class ChangePackageApprovalExpiry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_ids: list[str] = Field(default_factory=list, max_length=20)
    reason: str = Field(default="Approval request expired.", max_length=1200)


class ChangePackageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    branch_id: str
    change_set_id: str
    release_candidate_id: str
    from_version_id: str
    to_version_id: str
    commitment_document_id: str
    commitment_document_version: int
    summary: str
    semantic_diff: list[dict[str, Any]]
    eval_results_ref: str
    replay_results_ref: str
    risk_summary: str
    cost_summary: str
    latency_summary: str
    channel_readiness_summary: str
    tool_changes: list[dict[str, Any]]
    memory_changes: list[dict[str, Any]]
    knowledge_changes: list[dict[str, Any]]
    required_approvals: list[dict[str, Any]]
    pre_approved_classes: list[dict[str, Any]]
    approval_status: str
    rollback_target_version_id: str
    evidence_pack_id: str
    evidence: dict[str, str]
    content_hash: str
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    stale_at: datetime | None = None


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _default_semantic_diff(body: ChangePackageGenerate) -> list[dict[str, Any]]:
    if body.semantic_diff:
        return body.semantic_diff
    return [
        {
            "dimension": "behavior",
            "summary": "Draft behavior is ready for replay comparison.",
            "evidence_ref": body.replay_results_ref,
        },
        {
            "dimension": "channels",
            "summary": "Channel readiness must be checked before canary.",
            "evidence_ref": "channels/readiness",
        },
    ]


def _required_approvals(
    commitment: CommitmentDocumentRecord,
    body: ChangePackageGenerate,
    pre_approved_classes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    high_risk = body.target_environment == "production" or commitment.status != "accepted"
    covered = bool(pre_approved_classes) and commitment.status == "accepted"
    preapproval_reason = (
        f"Covered by pre-approved class {pre_approved_classes[0]['id']}." if covered else ""
    )
    return [
        {
            "id": "owner",
            "role": "Agent owner",
            "required": True,
            "satisfied": covered,
            "state": "pre_approved" if covered else "requested",
            "reason": preapproval_reason or f"Owner must approve Commitment v{commitment.version}.",
        },
        {
            "id": "compliance",
            "role": "Compliance reviewer",
            "required": high_risk and not covered,
            "satisfied": covered,
            "state": "pre_approved" if covered else ("requested" if high_risk else "not_required"),
            "reason": preapproval_reason
            or "Required for production or unaccepted commitment changes.",
        },
    ]


def infer_change_types(body: ChangePackageGenerate) -> list[str]:
    change_types = {
        str(row.get("dimension", "")).strip().lower()
        for row in body.semantic_diff
        if row.get("dimension")
    }
    if body.tool_changes:
        change_types.add("tool")
    if body.memory_changes:
        change_types.add("memory")
    if body.knowledge_changes:
        change_types.add("knowledge")
    if body.channel_readiness_summary:
        change_types.add("channel")
    if not change_types:
        change_types.add("instruction")
    return sorted(change_types)


def infer_change_risk(body: ChangePackageGenerate) -> str:
    if body.tool_changes or body.memory_changes:
        return "high"
    if body.target_environment == "production" and (
        "pii" in body.risk_summary.lower() or "payment" in body.risk_summary.lower()
    ):
        return "high"
    if body.target_environment == "production":
        return "low"
    return "low"


def _approval_status(approvals: list[dict[str, Any]]) -> str:
    required = [item for item in approvals if item.get("required")]
    if not required:
        return "not_required"
    approved = [item for item in required if item.get("satisfied")]
    if len(approved) == len(required):
        return "approved"
    if approved:
        return "partially_approved"
    return "blocked"


def _invalidate_approvals(
    approvals: list[dict[str, Any]],
    *,
    now: datetime,
    reason: str,
) -> list[dict[str, Any]]:
    invalidated: list[dict[str, Any]] = []
    for approval in approvals:
        if approval.get("satisfied") or approval.get("state") == "approved":
            invalidated.append(
                {
                    **approval,
                    "satisfied": False,
                    "state": "invalidated",
                    "invalidated_at": now.isoformat(),
                    "invalidated_reason": reason,
                }
            )
        else:
            invalidated.append(approval)
    return invalidated


def build_change_package(
    *,
    agent: AgentRecord,
    commitment: CommitmentDocumentRecord,
    body: ChangePackageGenerate,
    package_id: str,
    status: str,
    created_at: datetime,
    updated_at: datetime,
    pre_approved_classes: list[dict[str, Any]] | None = None,
) -> ChangePackageRecord:
    semantic_diff = _default_semantic_diff(body)
    summary = body.summary or (
        f"Promotes {agent.name} from {body.from_version_id} to "
        f"{body.to_version_id} for {body.target_environment}."
    )
    risk_summary = body.risk_summary or (
        "Blocked until the Commitment Document is accepted."
        if commitment.status != "accepted"
        else "No unresolved commitment blocker detected."
    )
    cost_summary = body.cost_summary or "No cost increase claimed without usage evidence."
    latency_summary = (
        body.latency_summary or "No latency regression claimed without trace evidence."
    )
    channel_summary = body.channel_readiness_summary or (
        "At least one channel readiness check must pass before canary."
    )
    preapprovals = pre_approved_classes or []
    evidence = {
        "commitment": commitment.id,
        "semantic_diff": "change_package.semantic_diff",
        "eval_results": body.eval_results_ref,
        "replay_results": body.replay_results_ref,
        "risk": "change_package.risk_summary",
        "cost": "change_package.cost_summary",
        "latency": "change_package.latency_summary",
        "channels": "change_package.channel_readiness_summary",
        "rollback": body.rollback_target_version_id,
        "change_set": body.change_set_id,
        "release_candidate": body.release_candidate_id,
        "pre_approved_classes": ",".join(item["id"] for item in preapprovals),
    }
    claims = {
        "agent_id": str(agent.id),
        "branch_id": body.branch_id,
        "change_set_id": body.change_set_id,
        "release_candidate_id": body.release_candidate_id,
        "from_version_id": body.from_version_id,
        "to_version_id": body.to_version_id,
        "commitment_document_id": commitment.id,
        "commitment_document_version": commitment.version,
        "summary": summary,
        "semantic_diff": semantic_diff,
        "eval_results_ref": body.eval_results_ref,
        "replay_results_ref": body.replay_results_ref,
        "risk_summary": risk_summary,
        "cost_summary": cost_summary,
        "latency_summary": latency_summary,
        "channel_readiness_summary": channel_summary,
        "tool_changes": body.tool_changes,
        "memory_changes": body.memory_changes,
        "knowledge_changes": body.knowledge_changes,
        "required_approvals": _required_approvals(commitment, body, preapprovals),
        "pre_approved_classes": preapprovals,
        "rollback_target_version_id": body.rollback_target_version_id,
        "evidence": evidence,
    }
    content_hash = _hash_payload(claims)
    return ChangePackageRecord(
        id=package_id,
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
        branch_id=body.branch_id,
        change_set_id=body.change_set_id,
        release_candidate_id=body.release_candidate_id,
        from_version_id=body.from_version_id,
        to_version_id=body.to_version_id,
        commitment_document_id=commitment.id,
        commitment_document_version=commitment.version,
        summary=summary,
        semantic_diff=semantic_diff,
        eval_results_ref=body.eval_results_ref,
        replay_results_ref=body.replay_results_ref,
        risk_summary=risk_summary,
        cost_summary=cost_summary,
        latency_summary=latency_summary,
        channel_readiness_summary=channel_summary,
        tool_changes=body.tool_changes,
        memory_changes=body.memory_changes,
        knowledge_changes=body.knowledge_changes,
        required_approvals=claims["required_approvals"],
        pre_approved_classes=preapprovals,
        approval_status=_approval_status(claims["required_approvals"]),
        rollback_target_version_id=body.rollback_target_version_id,
        evidence_pack_id=f"ep_{package_id.removeprefix('cp_')}",
        evidence=evidence,
        content_hash=content_hash,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )


def change_package_payload(record: ChangePackageRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class ChangePackageRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, list[ChangePackageRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[ChangePackageRecord]:
        async with self._lock:
            return list(self._items.get(agent.id, []))

    async def current(self, *, agent: AgentRecord) -> ChangePackageRecord | None:
        async with self._lock:
            items = self._items.get(agent.id, [])
            return items[-1] if items else None

    async def generate(
        self,
        *,
        agent: AgentRecord,
        commitment: CommitmentDocumentRecord,
        body: ChangePackageGenerate,
        pre_approved_classes: list[dict[str, Any]] | None = None,
    ) -> ChangePackageRecord:
        async with self._lock:
            now = datetime.now(UTC)
            existing_items = self._items.setdefault(agent.id, [])
            candidate = build_change_package(
                agent=agent,
                commitment=commitment,
                body=body,
                package_id=f"cp_{uuid4().hex[:12]}",
                status="generated",
                created_at=now,
                updated_at=now,
                pre_approved_classes=pre_approved_classes,
            )
            if existing_items:
                latest = existing_items[-1]
                if latest.content_hash == candidate.content_hash and latest.status != "stale":
                    return latest
                if latest.status in {"generated", "submitted", "approved", "deployable"}:
                    existing_items[-1] = latest.model_copy(
                        update={
                            "status": "stale",
                            "approval_status": "stale",
                            "required_approvals": _invalidate_approvals(
                                latest.required_approvals,
                                now=now,
                                reason="A newer Change Package changed the content hash.",
                            ),
                            "stale_at": now,
                            "updated_at": now,
                        }
                    )
            existing_items.append(candidate)
            return candidate

    async def submit(self, *, agent: AgentRecord, package_id: str) -> ChangePackageRecord:
        async with self._lock:
            items = self._items.get(agent.id, [])
            for index, item in enumerate(items):
                if item.id != package_id:
                    continue
                if item.status != "generated":
                    raise WorkspaceError(
                        f"change package {package_id} cannot be submitted from {item.status}"
                    )
                now = datetime.now(UTC)
                submitted = item.model_copy(
                    update={"status": "submitted", "submitted_at": now, "updated_at": now}
                )
                items[index] = submitted
                return submitted
        raise WorkspaceError(f"unknown change package: {package_id}")

    async def record_approval(
        self,
        *,
        agent: AgentRecord,
        package_id: str,
        action: ChangePackageApprovalAction,
        actor_sub: str,
    ) -> ChangePackageRecord:
        async with self._lock:
            items = self._items.get(agent.id, [])
            for index, item in enumerate(items):
                if item.id != package_id:
                    continue
                if item.status == "stale":
                    raise WorkspaceError(
                        f"change package {package_id} is stale and cannot be approved"
                    )
                if item.status not in {"submitted", "approved", "deployable"}:
                    raise WorkspaceError(
                        f"change package {package_id} must be submitted before approval"
                    )
                now = datetime.now(UTC)
                approvals = list(item.required_approvals)
                updated = False
                for approval_index, approval in enumerate(approvals):
                    if approval.get("id") != action.approval_id:
                        continue
                    updated = True
                    if action.decision == "approve":
                        approvals[approval_index] = {
                            **approval,
                            "satisfied": True,
                            "state": "approved",
                            "actor_sub": actor_sub,
                            "decided_at": now.isoformat(),
                            "content_hash": item.content_hash,
                            "comment": action.comment,
                        }
                    elif action.decision == "revoke":
                        approvals[approval_index] = {
                            **approval,
                            "satisfied": False,
                            "state": "revoked",
                            "actor_sub": actor_sub,
                            "decided_at": now.isoformat(),
                            "content_hash": item.content_hash,
                            "comment": action.comment,
                        }
                    else:
                        approvals[approval_index] = {
                            **approval,
                            "satisfied": False,
                            "state": action.decision,
                            "actor_sub": actor_sub,
                            "decided_at": now.isoformat(),
                            "content_hash": item.content_hash,
                            "comment": action.comment,
                        }
                    break
                if not updated:
                    raise WorkspaceError(f"unknown approval requirement: {action.approval_id}")

                approval_status = _approval_status(approvals)
                status = item.status
                if action.decision == "approve" and approval_status == "approved":
                    status = "approved"
                elif action.decision == "approve":
                    status = "submitted"
                elif action.decision in {"reject", "request_changes"}:
                    approval_status = action.decision
                    status = "changes_requested"
                elif action.decision == "revoke":
                    approval_status = "revoked"
                    status = "revoked"

                reviewed = item.model_copy(
                    update={
                        "required_approvals": approvals,
                        "approval_status": approval_status,
                        "status": status,
                        "updated_at": now,
                    }
                )
                items[index] = reviewed
                return reviewed
        raise WorkspaceError(f"unknown change package: {package_id}")

    async def expire_approvals(
        self,
        *,
        agent: AgentRecord,
        package_id: str,
        body: ChangePackageApprovalExpiry,
    ) -> ChangePackageRecord:
        async with self._lock:
            items = self._items.get(agent.id, [])
            target_ids = set(body.approval_ids)
            for index, item in enumerate(items):
                if item.id != package_id:
                    continue
                if item.status == "stale":
                    raise WorkspaceError(
                        f"change package {package_id} is stale and cannot expire approvals"
                    )
                if item.status not in {"submitted", "approved", "deployable"}:
                    raise WorkspaceError(
                        f"change package {package_id} must be submitted before approval expiry"
                    )
                now = datetime.now(UTC)
                approvals: list[dict[str, Any]] = []
                expired_ids: list[str] = []
                for approval in item.required_approvals:
                    approval_id = str(approval.get("id", "approval"))
                    should_expire = (
                        approval.get("required")
                        and not approval.get("satisfied")
                        and approval.get("state") == "requested"
                        and (not target_ids or approval_id in target_ids)
                    )
                    if should_expire:
                        expired_ids.append(approval_id)
                        approvals.append(
                            {
                                **approval,
                                "satisfied": False,
                                "state": "expired",
                                "expired_at": now.isoformat(),
                                "expired_reason": body.reason,
                            }
                        )
                    else:
                        approvals.append(approval)
                if not expired_ids:
                    raise WorkspaceError(
                        f"change package {package_id} has no requested approvals to expire"
                    )
                expired = item.model_copy(
                    update={
                        "required_approvals": approvals,
                        "approval_status": "expired",
                        "status": "changes_requested",
                        "updated_at": now,
                    }
                )
                items[index] = expired
                return expired
        raise WorkspaceError(f"unknown change package: {package_id}")
