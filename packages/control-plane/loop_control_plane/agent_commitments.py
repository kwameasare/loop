from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

REQUIRED_COMMITMENT_FIELDS = (
    "business_responsibility",
    "target_users",
    "owner_user_id",
    "worst_case_failure",
    "channels",
    "systems_touched",
    "regions",
    "languages",
)


class CommitmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_responsibility: str = Field(default="", max_length=2000)
    target_users: str = Field(default="", max_length=1000)
    owner_user_id: str = Field(default="", max_length=256)
    backup_owner_user_id: str = Field(default="", max_length=256)
    worst_case_failure: str = Field(default="", max_length=1000)
    channels: list[str] = Field(default_factory=list, max_length=20)
    systems_touched: list[str] = Field(default_factory=list, max_length=30)
    regions: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=list, max_length=20)
    success_metric: str = Field(default="", max_length=1000)
    compliance_domain: str = Field(default="", max_length=512)
    expected_volume: str = Field(default="", max_length=512)
    launch_date: str = Field(default="", max_length=128)
    budget_target: str = Field(default="", max_length=512)
    out_of_scope: str = Field(default="", max_length=1200)
    escalation_policy: str = Field(default="", max_length=1200)


class CommitmentDocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    agent_id: UUID
    workspace_id: UUID
    version: int
    body: CommitmentBody
    structured_summary: dict[str, Any]
    owner_user_id: str
    status: str
    content_hash: str
    created_from: str
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None = None
    superseded_at: datetime | None = None


def missing_required_fields(body: CommitmentBody) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_COMMITMENT_FIELDS:
        value = getattr(body, field)
        if isinstance(value, list):
            if not [item for item in value if item.strip()]:
                missing.append(field)
        elif not str(value).strip():
            missing.append(field)
    return missing


def commitment_hash(body: CommitmentBody) -> str:
    return sha256(body.model_dump_json().encode("utf-8")).hexdigest()


def structured_summary(body: CommitmentBody) -> dict[str, Any]:
    missing = missing_required_fields(body)
    return {
        "responsibility": body.business_responsibility.strip(),
        "audience": body.target_users.strip(),
        "owner": body.owner_user_id.strip(),
        "backup_owner": body.backup_owner_user_id.strip(),
        "risk": body.worst_case_failure.strip(),
        "channels": [item.strip() for item in body.channels if item.strip()],
        "systems_touched": [item.strip() for item in body.systems_touched if item.strip()],
        "regions": [item.strip() for item in body.regions if item.strip()],
        "languages": [item.strip() for item in body.languages if item.strip()],
        "readiness": "complete" if not missing else "incomplete",
        "missing_required_fields": missing,
    }


def seed_body_for_agent(agent: AgentRecord) -> CommitmentBody:
    return CommitmentBody(
        business_responsibility=agent.description.strip(),
        target_users="",
        owner_user_id="",
        worst_case_failure="",
        channels=[],
        systems_touched=[],
        regions=[],
        languages=[],
    )


def commitment_payload(record: CommitmentDocumentRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class CommitmentRegistry:
    """Process-local Commitment Document registry.

    The object shape is intentionally stricter than the current storage
    backend. Routes, Studio clients, and tests can build against the real
    contract now; a future Postgres implementation can preserve the same
    async surface and payloads.
    """

    def __init__(self) -> None:
        self._items: dict[UUID, list[CommitmentDocumentRecord]] = {}
        self._lock = asyncio.Lock()

    async def ensure_current(
        self,
        *,
        agent: AgentRecord,
        created_from: str,
        body: CommitmentBody | None = None,
    ) -> CommitmentDocumentRecord:
        async with self._lock:
            existing = self._current_unlocked(agent.id)
            if existing is not None:
                return existing
            now = datetime.now(UTC)
            draft_body = body or seed_body_for_agent(agent)
            record = CommitmentDocumentRecord(
                id=f"commit_{uuid4().hex[:12]}",
                agent_id=agent.id,
                workspace_id=agent.workspace_id,
                version=1,
                body=draft_body,
                structured_summary=structured_summary(draft_body),
                owner_user_id=draft_body.owner_user_id,
                status="draft",
                content_hash=commitment_hash(draft_body),
                created_from=created_from,
                created_at=now,
                updated_at=now,
            )
            self._items.setdefault(agent.id, []).append(record)
            return record

    async def current(self, *, agent: AgentRecord) -> CommitmentDocumentRecord:
        record = await self.ensure_current(agent=agent, created_from="agent:read")
        return record

    async def save_draft(
        self,
        *,
        agent: AgentRecord,
        body: CommitmentBody,
        created_from: str,
    ) -> CommitmentDocumentRecord:
        async with self._lock:
            now = datetime.now(UTC)
            items = self._items.setdefault(agent.id, [])
            current = self._current_unlocked(agent.id)
            if current is None:
                version = 1
                created_at = now
                updated_items = items
            elif current.status == "draft":
                version = current.version
                created_at = current.created_at
                updated_items = [item for item in items if item.id != current.id]
            else:
                version = current.version + 1
                created_at = now
                superseded = current.model_copy(
                    update={"status": "superseded", "superseded_at": now, "updated_at": now}
                )
                updated_items = [superseded if item.id == current.id else item for item in items]
            record = CommitmentDocumentRecord(
                id=current.id
                if current is not None and current.status == "draft"
                else f"commit_{uuid4().hex[:12]}",
                agent_id=agent.id,
                workspace_id=agent.workspace_id,
                version=version,
                body=body,
                structured_summary=structured_summary(body),
                owner_user_id=body.owner_user_id,
                status="draft",
                content_hash=commitment_hash(body),
                created_from=created_from,
                created_at=created_at,
                updated_at=now,
            )
            updated_items.append(record)
            self._items[agent.id] = sorted(updated_items, key=lambda item: item.version)
            return record

    async def accept_current(
        self,
        *,
        agent: AgentRecord,
    ) -> CommitmentDocumentRecord:
        async with self._lock:
            current = self._current_unlocked(agent.id)
            if current is None:
                raise WorkspaceError(f"unknown commitment for agent: {agent.id}")
            missing = missing_required_fields(current.body)
            if missing:
                raise WorkspaceError("commitment is missing required fields: " + ", ".join(missing))
            now = datetime.now(UTC)
            accepted = current.model_copy(
                update={"status": "accepted", "accepted_at": now, "updated_at": now}
            )
            self._items[agent.id] = [
                accepted if item.id == current.id else item for item in self._items[agent.id]
            ]
            return accepted

    async def history(self, *, agent: AgentRecord) -> list[CommitmentDocumentRecord]:
        await self.ensure_current(agent=agent, created_from="agent:read")
        async with self._lock:
            return list(self._items.get(agent.id, []))

    def _current_unlocked(self, agent_id: UUID) -> CommitmentDocumentRecord | None:
        items = [
            item for item in self._items.get(agent_id, []) if item.status in {"draft", "accepted"}
        ]
        if not items:
            return None
        return sorted(items, key=lambda item: (item.version, item.updated_at))[-1]
