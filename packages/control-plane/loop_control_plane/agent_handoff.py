from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError


class OwnershipTransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_owner_user_id: str = Field(min_length=1, max_length=256)
    backup_owner_user_id: str = Field(default="", max_length=256)
    reason: str = Field(default="", max_length=1200)
    acknowledged_risk_ids: list[str] = Field(default_factory=list, max_length=50)


class OwnershipTransferRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    previous_owner_user_id: str
    new_owner_user_id: str
    backup_owner_user_id: str
    reason: str
    acknowledged_risk_ids: list[str]
    open_risk_ids: list[str]
    walkthrough_section_ids: list[str]
    notification: dict[str, str]
    history_walkthrough_id: str
    created_by_user_id: str
    created_at: datetime


class AgentHandoffRegistry:
    def __init__(self) -> None:
        self._transfers: dict[UUID, list[OwnershipTransferRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[OwnershipTransferRecord]:
        async with self._lock:
            return list(self._transfers.get(agent.id, []))

    async def create_transfer(
        self,
        *,
        agent: AgentRecord,
        previous_owner_user_id: str,
        body: OwnershipTransferCreate,
        actor_sub: str,
        open_risk_ids: list[str] | None = None,
        walkthrough_section_ids: list[str] | None = None,
    ) -> OwnershipTransferRecord:
        if previous_owner_user_id == body.new_owner_user_id:
            raise WorkspaceError("new owner already owns this agent")
        async with self._lock:
            now = datetime.now(UTC)
            record = OwnershipTransferRecord(
                id=f"handoff_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                previous_owner_user_id=previous_owner_user_id,
                new_owner_user_id=body.new_owner_user_id,
                backup_owner_user_id=body.backup_owner_user_id,
                reason=body.reason,
                acknowledged_risk_ids=body.acknowledged_risk_ids,
                open_risk_ids=open_risk_ids or [],
                walkthrough_section_ids=walkthrough_section_ids or [],
                notification={
                    "recipient": body.new_owner_user_id,
                    "channel": "in_app",
                    "status": "queued",
                    "sent_at": now.isoformat(),
                    "summary": "Agent ownership transferred. Review the history walkthrough before editing.",
                },
                history_walkthrough_id=f"walk_{uuid4().hex[:12]}",
                created_by_user_id=actor_sub,
                created_at=now,
            )
            self._transfers.setdefault(agent.id, []).insert(0, record)
            return record


def transfer_payload(record: OwnershipTransferRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")
