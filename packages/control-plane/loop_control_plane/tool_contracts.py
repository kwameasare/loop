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

ToolSideEffectLevel = Literal[
    "unknown",
    "read",
    "write",
    "money_movement",
    "external_message",
]
SandboxStatus = Literal["mock", "sandbox", "disabled"]
LiveStatus = Literal["disabled", "review_required", "approved", "blocked"]


class ToolContractUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1200)
    side_effect_level: ToolSideEffectLevel = "unknown"
    pii_access: bool = False
    money_movement: bool = False
    rate_limits: dict[str, Any] = Field(default_factory=dict)
    budget_limits: dict[str, Any] = Field(default_factory=dict)
    sandbox_status: SandboxStatus = "sandbox"
    owner_user_id: str = Field(default="", max_length=160)
    approval_policy_id: str = Field(default="", max_length=160)
    failure_behavior: str = Field(default="", max_length=1200)
    compensation_behavior: str = Field(default="", max_length=1200)


class ToolContractRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    tool_id: str
    name: str
    description: str
    side_effect_level: ToolSideEffectLevel
    pii_access: bool
    money_movement: bool
    rate_limits: dict[str, Any]
    budget_limits: dict[str, Any]
    sandbox_status: SandboxStatus
    live_status: LiveStatus
    owner_user_id: str
    approval_policy_id: str
    failure_behavior: str
    compensation_behavior: str
    content_hash: str
    approval_invalidated_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _content_hash(body: ToolContractUpsert) -> str:
    payload = {
        "name": body.name,
        "description": body.description,
        "side_effect_level": body.side_effect_level,
        "pii_access": body.pii_access,
        "money_movement": body.money_movement,
        "rate_limits": body.rate_limits,
        "budget_limits": body.budget_limits,
        "sandbox_status": body.sandbox_status,
        "owner_user_id": body.owner_user_id,
        "approval_policy_id": body.approval_policy_id,
        "failure_behavior": body.failure_behavior,
        "compensation_behavior": body.compensation_behavior,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _live_status_for(body: ToolContractUpsert) -> LiveStatus:
    if body.side_effect_level == "unknown":
        return "review_required"
    if body.money_movement and not body.budget_limits:
        return "blocked"
    if body.side_effect_level != "read" and not body.failure_behavior:
        return "review_required"
    return "disabled"


def _promotion_blocker(record: ToolContractRecord) -> str | None:
    if record.side_effect_level == "unknown":
        return "side-effect classification is required"
    if record.money_movement and not record.budget_limits:
        return "money-moving tools require budget caps"
    if record.side_effect_level != "read" and not record.failure_behavior:
        return "mutating tools require failure behavior"
    if record.money_movement and not record.compensation_behavior:
        return "money-moving tools require compensation behavior"
    if not record.owner_user_id:
        return "tool owner is required"
    return None


def tool_contract_payload(record: ToolContractRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class ToolContractRegistry:
    def __init__(self) -> None:
        self._contracts: dict[UUID, list[ToolContractRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[ToolContractRecord]:
        async with self._lock:
            return list(self._contracts.get(agent.id, []))

    async def upsert(
        self,
        *,
        agent: AgentRecord,
        tool_id: str,
        body: ToolContractUpsert,
    ) -> ToolContractRecord:
        async with self._lock:
            now = datetime.now(UTC)
            contracts = self._contracts.setdefault(agent.id, [])
            content_hash = _content_hash(body)
            existing_index = next(
                (index for index, contract in enumerate(contracts) if contract.tool_id == tool_id),
                None,
            )
            if existing_index is None:
                record = ToolContractRecord(
                    id=f"tc_{uuid4().hex[:12]}",
                    workspace_id=agent.workspace_id,
                    agent_id=agent.id,
                    tool_id=tool_id,
                    name=body.name,
                    description=body.description,
                    side_effect_level=body.side_effect_level,
                    pii_access=body.pii_access,
                    money_movement=body.money_movement,
                    rate_limits=body.rate_limits,
                    budget_limits=body.budget_limits,
                    sandbox_status=body.sandbox_status,
                    live_status=_live_status_for(body),
                    owner_user_id=body.owner_user_id,
                    approval_policy_id=body.approval_policy_id,
                    failure_behavior=body.failure_behavior,
                    compensation_behavior=body.compensation_behavior,
                    content_hash=content_hash,
                    approval_invalidated_at=None,
                    created_at=now,
                    updated_at=now,
                )
                contracts.insert(0, record)
                return record

            existing = contracts[existing_index]
            approval_invalidated_at = existing.approval_invalidated_at
            live_status = _live_status_for(body)
            if existing.live_status == "approved" and existing.content_hash != content_hash:
                approval_invalidated_at = now
                live_status = "review_required"
            record = existing.model_copy(
                update={
                    "name": body.name,
                    "description": body.description,
                    "side_effect_level": body.side_effect_level,
                    "pii_access": body.pii_access,
                    "money_movement": body.money_movement,
                    "rate_limits": body.rate_limits,
                    "budget_limits": body.budget_limits,
                    "sandbox_status": body.sandbox_status,
                    "live_status": live_status,
                    "owner_user_id": body.owner_user_id,
                    "approval_policy_id": body.approval_policy_id,
                    "failure_behavior": body.failure_behavior,
                    "compensation_behavior": body.compensation_behavior,
                    "content_hash": content_hash,
                    "approval_invalidated_at": approval_invalidated_at,
                    "updated_at": now,
                }
            )
            contracts[existing_index] = record
            return record

    async def promote(self, *, agent: AgentRecord, tool_id: str) -> ToolContractRecord:
        async with self._lock:
            contracts = self._contracts.get(agent.id, [])
            for index, contract in enumerate(contracts):
                if contract.tool_id != tool_id:
                    continue
                blocker = _promotion_blocker(contract)
                if blocker is not None:
                    raise WorkspaceError(blocker)
                updated = contract.model_copy(
                    update={
                        "live_status": "approved",
                        "approval_invalidated_at": None,
                        "updated_at": datetime.now(UTC),
                    }
                )
                contracts[index] = updated
                return updated
        raise WorkspaceError(f"unknown tool contract: {tool_id}")
