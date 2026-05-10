from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

MemoryPolicyScope = Literal[
    "turn",
    "conversation",
    "session",
    "user",
    "account",
    "organization",
    "task",
    "agent",
    "workspace",
]
MemoryPolicyApprovalStatus = Literal["draft", "review_required", "approved", "blocked"]

DURABLE_SCOPES: set[MemoryPolicyScope] = {
    "user",
    "account",
    "organization",
    "agent",
    "workspace",
}


class MemoryPolicyUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: MemoryPolicyScope
    allowed_memory_types: list[str] = Field(default_factory=list, max_length=25)
    retention: str = Field(min_length=1, max_length=500)
    consent_requirement: str = Field(min_length=1, max_length=500)
    pii_policy: str = Field(min_length=1, max_length=500)
    delete_behavior: str = Field(min_length=1, max_length=500)
    privacy_implications: list[str] = Field(default_factory=list, max_length=10)
    source_trace_required: bool = True


class MemoryPolicyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    scope: MemoryPolicyScope
    allowed_memory_types: list[str]
    retention: str
    consent_requirement: str
    pii_policy: str
    delete_behavior: str
    privacy_implications: list[str]
    source_trace_required: bool
    approval_status: MemoryPolicyApprovalStatus
    content_hash: str
    approval_invalidated_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _content_hash(body: MemoryPolicyUpsert) -> str:
    encoded = json.dumps(
        body.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _approval_status_for(body: MemoryPolicyUpsert) -> MemoryPolicyApprovalStatus:
    if not body.allowed_memory_types:
        return "blocked"
    if not body.source_trace_required:
        return "blocked"
    lowered = " ".join(
        [
            body.consent_requirement,
            body.pii_policy,
            body.delete_behavior,
            *body.privacy_implications,
        ]
    ).lower()
    if body.scope in DURABLE_SCOPES and (
        not body.privacy_implications
        or "delete" not in body.delete_behavior.lower()
        or "consent" not in body.consent_requirement.lower()
    ):
        return "review_required"
    if any(token in lowered for token in ("pii", "personal", "identifier", "email")):
        return "review_required"
    return "draft"


def _approval_blocker(record: MemoryPolicyRecord) -> str | None:
    if not record.allowed_memory_types:
        return "allowed memory types are required"
    if not record.source_trace_required:
        return "durable memory writes must remain trace-backed"
    if record.scope in DURABLE_SCOPES:
        if not record.privacy_implications:
            return "privacy implications must be shown before durable activation"
        if "delete" not in record.delete_behavior.lower():
            return "durable memory requires explicit delete behavior"
        if "consent" not in record.consent_requirement.lower():
            return "durable memory requires explicit consent requirement"
    return None


def memory_policy_payload(record: MemoryPolicyRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class MemoryPolicyRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, dict[MemoryPolicyScope, MemoryPolicyRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[MemoryPolicyRecord]:
        async with self._lock:
            return list(self._items.get(agent.id, {}).values())

    async def upsert(
        self,
        *,
        agent: AgentRecord,
        body: MemoryPolicyUpsert,
    ) -> MemoryPolicyRecord:
        async with self._lock:
            now = datetime.now(UTC)
            by_scope = self._items.setdefault(agent.id, {})
            existing = by_scope.get(body.scope)
            content_hash = _content_hash(body)
            approval_invalidated_at = (
                existing.approval_invalidated_at if existing is not None else None
            )
            approval_status = _approval_status_for(body)
            if (
                existing is not None
                and existing.approval_status == "approved"
                and existing.content_hash != content_hash
            ):
                approval_invalidated_at = now
                approval_status = "review_required"

            record = MemoryPolicyRecord(
                id=existing.id if existing is not None else f"mp_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                scope=body.scope,
                allowed_memory_types=body.allowed_memory_types,
                retention=body.retention,
                consent_requirement=body.consent_requirement,
                pii_policy=body.pii_policy,
                delete_behavior=body.delete_behavior,
                privacy_implications=body.privacy_implications,
                source_trace_required=body.source_trace_required,
                approval_status=approval_status,
                content_hash=content_hash,
                approval_invalidated_at=approval_invalidated_at,
                created_at=existing.created_at if existing is not None else now,
                updated_at=now,
            )
            by_scope[body.scope] = record
            return record

    async def approve(
        self,
        *,
        agent: AgentRecord,
        scope: MemoryPolicyScope,
    ) -> MemoryPolicyRecord:
        async with self._lock:
            record = self._items.get(agent.id, {}).get(scope)
            if record is None:
                raise WorkspaceError(f"unknown memory policy scope: {scope}")
            blocker = _approval_blocker(record)
            if blocker is not None:
                raise WorkspaceError(blocker)
            updated = record.model_copy(
                update={
                    "approval_status": "approved",
                    "approval_invalidated_at": None,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._items[agent.id][scope] = updated
            return updated
