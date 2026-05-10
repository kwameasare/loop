from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

RiskCeiling = Literal["low", "medium", "high"]
PreApprovedClassStatus = Literal["active", "revoked", "expired", "invalidated"]

_RISK_ORDER: dict[RiskCeiling, int] = {"low": 1, "medium": 2, "high": 3}


class PreApprovedClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted_to_user_id: str = Field(default="", max_length=256)
    team_id: str = Field(default="", max_length=256)
    allowed_change_types: list[str] = Field(min_length=1, max_length=24)
    excluded_change_types: list[str] = Field(default_factory=list, max_length=24)
    risk_ceiling: RiskCeiling = "low"
    expires_at: datetime
    reason: str = Field(default="", max_length=1200)

    @model_validator(mode="after")
    def _has_grantee(self) -> PreApprovedClassCreate:
        if not self.granted_to_user_id.strip() and not self.team_id.strip():
            raise ValueError("pre-approved class requires a user or team grantee")
        return self


class PreApprovedClassRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    granted_by_user_id: str
    granted_to_user_id: str
    team_id: str
    allowed_change_types: list[str]
    excluded_change_types: list[str]
    risk_ceiling: RiskCeiling
    expires_at: datetime
    status: PreApprovedClassStatus
    reason: str
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
    invalidated_at: datetime | None = None
    used_by_change_packages: list[str] = Field(default_factory=list)


def _normalise(items: list[str]) -> list[str]:
    return sorted({item.strip().lower() for item in items if item.strip()})


def preapproved_class_payload(record: PreApprovedClassRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def _is_expired(record: PreApprovedClassRecord, now: datetime) -> bool:
    return record.expires_at <= now


def _risk_allows(record: PreApprovedClassRecord, risk: RiskCeiling) -> bool:
    return _RISK_ORDER[record.risk_ceiling] >= _RISK_ORDER[risk]


class PreApprovedClassRegistry:
    def __init__(self) -> None:
        self._items: dict[UUID, list[PreApprovedClassRecord]] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        agent: AgentRecord,
        body: PreApprovedClassCreate,
        actor_sub: str,
    ) -> PreApprovedClassRecord:
        now = datetime.now(UTC)
        if body.expires_at <= now:
            raise WorkspaceError("pre-approved class must expire in the future")
        if body.expires_at > now + timedelta(days=30):
            raise WorkspaceError("pre-approved class cannot exceed 30 days")
        if body.risk_ceiling == "high":
            raise WorkspaceError("pre-approved class cannot cover high-risk changes")
        allowed = _normalise(body.allowed_change_types)
        excluded = _normalise(body.excluded_change_types)
        if not allowed:
            raise WorkspaceError("pre-approved class requires allowed change types")
        if not excluded:
            raise WorkspaceError("pre-approved class requires excluded change types")
        overlap = set(allowed).intersection(excluded)
        if overlap:
            raise WorkspaceError(
                f"change types cannot be both allowed and excluded: {sorted(overlap)[0]}"
            )
        async with self._lock:
            record = PreApprovedClassRecord(
                id=f"pac_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                granted_by_user_id=actor_sub,
                granted_to_user_id=body.granted_to_user_id,
                team_id=body.team_id,
                allowed_change_types=allowed,
                excluded_change_types=excluded,
                risk_ceiling=body.risk_ceiling,
                expires_at=body.expires_at,
                status="active",
                reason=body.reason,
                created_at=now,
                updated_at=now,
            )
            self._items.setdefault(agent.id, []).insert(0, record)
            return record

    async def list_for_agent(self, *, agent: AgentRecord) -> list[PreApprovedClassRecord]:
        async with self._lock:
            now = datetime.now(UTC)
            rows = self._items.get(agent.id, [])
            updated: list[PreApprovedClassRecord] = []
            changed = False
            for record in rows:
                if record.status == "active" and _is_expired(record, now):
                    updated.append(
                        record.model_copy(update={"status": "expired", "updated_at": now})
                    )
                    changed = True
                else:
                    updated.append(record)
            if changed:
                self._items[agent.id] = updated
            return list(updated)

    async def revoke(
        self,
        *,
        agent: AgentRecord,
        class_id: str,
    ) -> PreApprovedClassRecord:
        async with self._lock:
            rows = self._items.get(agent.id, [])
            for index, record in enumerate(rows):
                if record.id != class_id:
                    continue
                now = datetime.now(UTC)
                revoked = record.model_copy(
                    update={
                        "status": "revoked",
                        "revoked_at": now,
                        "updated_at": now,
                    }
                )
                rows[index] = revoked
                return revoked
        raise WorkspaceError(f"unknown pre-approved class: {class_id}")

    async def applicable(
        self,
        *,
        agent: AgentRecord,
        change_types: list[str],
        risk: RiskCeiling,
        actor_sub: str,
    ) -> list[PreApprovedClassRecord]:
        requested = _normalise(change_types)
        rows = await self.list_for_agent(agent=agent)
        matches: list[PreApprovedClassRecord] = []
        for record in rows:
            if record.status != "active":
                continue
            if record.granted_to_user_id and record.granted_to_user_id != actor_sub:
                continue
            if not _risk_allows(record, risk):
                continue
            if set(requested).difference(record.allowed_change_types):
                continue
            if set(requested).intersection(record.excluded_change_types):
                continue
            matches.append(record)
        return matches

    async def mark_used(
        self,
        *,
        agent: AgentRecord,
        class_ids: list[str],
        package_id: str,
    ) -> list[PreApprovedClassRecord]:
        if not class_ids:
            return []
        async with self._lock:
            rows = self._items.get(agent.id, [])
            updated_rows = list(rows)
            touched: list[PreApprovedClassRecord] = []
            for index, record in enumerate(rows):
                if record.id not in class_ids:
                    continue
                used = record.model_copy(
                    update={
                        "used_by_change_packages": sorted(
                            {*record.used_by_change_packages, package_id}
                        ),
                        "updated_at": datetime.now(UTC),
                    }
                )
                updated_rows[index] = used
                touched.append(used)
            self._items[agent.id] = updated_rows
            return touched

    async def invalidate_for_change_types(
        self,
        *,
        agent: AgentRecord,
        change_types: list[str],
        reason: str,
    ) -> list[PreApprovedClassRecord]:
        requested = set(_normalise(change_types))
        if not requested:
            return []
        async with self._lock:
            rows = self._items.get(agent.id, [])
            updated_rows = list(rows)
            touched: list[PreApprovedClassRecord] = []
            now = datetime.now(UTC)
            for index, record in enumerate(rows):
                if record.status != "active":
                    continue
                scope = set(record.allowed_change_types) | set(
                    record.excluded_change_types
                )
                if not requested.intersection(scope):
                    continue
                invalidated = record.model_copy(
                    update={
                        "status": "invalidated",
                        "invalidated_at": now,
                        "updated_at": now,
                        "reason": f"{record.reason}\nInvalidated: {reason}".strip(),
                    }
                )
                updated_rows[index] = invalidated
                touched.append(invalidated)
            self._items[agent.id] = updated_rows
            return touched
