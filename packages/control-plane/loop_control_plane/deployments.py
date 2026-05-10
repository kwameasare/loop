from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.change_packages import ChangePackageRecord
from loop_control_plane.channel_bindings import ChannelType
from loop_control_plane.workspaces import WorkspaceError

DeploymentStatus = Literal[
    "pending",
    "shadow",
    "canary",
    "live",
    "paused",
    "rolled_back",
    "superseded",
]
DeploymentStage = Literal[
    "shadow", "canary", "ramp", "production", "rolled_back", "paused", "failed"
]


class DeploymentStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_package_id: str = Field(max_length=160)
    version_id: str = Field(default="", max_length=160)
    stage: Literal["shadow", "canary"] = "canary"
    traffic_percent: int = Field(default=5, ge=0, le=100)
    channel_scope: list[ChannelType] = Field(default_factory=list, max_length=20)
    region_scope: list[str] = Field(default_factory=list, max_length=20)
    segment_scope: list[str] = Field(default_factory=list, max_length=20)
    hold_time_minutes: int = Field(default=30, ge=0, le=1440)
    auto_rollback_thresholds: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=500)


class DeploymentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    version_id: str
    change_package_id: str
    evidence_pack_id: str
    stage: DeploymentStage
    status: DeploymentStatus
    traffic_percent: int
    channel_scope: list[ChannelType]
    region_scope: list[str]
    segment_scope: list[str]
    hold_time_minutes: int
    auto_rollback_thresholds: dict[str, Any]
    created_at: datetime
    promoted_at: datetime | None = None
    paused_at: datetime | None = None
    rolled_back_at: datetime | None = None
    notes: str | None = None


class EvidencePackRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    version_id: str
    deployment_id: str
    change_package_id: str
    version_manifest: dict[str, Any]
    behavior_diff_ref: str
    tool_permission_diff_ref: str
    knowledge_diff_ref: str
    memory_policy_ref: str
    channel_deployment_plan_ref: str
    eval_results_ref: str
    approval_records_ref: str
    canary_results_ref: str
    rollback_plan_ref: str
    audit_log_ref: str
    created_at: datetime
    export_formats: list[str]


def _deployment_payload(record: DeploymentRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "agentId": str(record.agent_id),
        "versionId": record.version_id,
        "changePackageId": record.change_package_id,
        "evidencePackId": record.evidence_pack_id,
        "stage": record.stage,
        "status": record.status,
        "trafficPercent": record.traffic_percent,
        "channelScope": record.channel_scope,
        "regionScope": record.region_scope,
        "segmentScope": record.segment_scope,
        "holdTimeMinutes": record.hold_time_minutes,
        "autoRollbackThresholds": record.auto_rollback_thresholds,
        "createdAt": record.created_at.isoformat(),
        "promotedAt": record.promoted_at.isoformat() if record.promoted_at else None,
        "pausedAt": record.paused_at.isoformat() if record.paused_at else None,
        "rolledBackAt": record.rolled_back_at.isoformat() if record.rolled_back_at else None,
        "notes": record.notes,
    }


def _evidence_payload(record: EvidencePackRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class DeploymentRegistry:
    def __init__(self) -> None:
        self._deployments: dict[UUID, list[DeploymentRecord]] = {}
        self._evidence_packs: dict[UUID, list[EvidencePackRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_agent(self, *, agent: AgentRecord) -> list[DeploymentRecord]:
        async with self._lock:
            return list(self._deployments.get(agent.id, []))

    async def list_evidence_packs(self, *, agent: AgentRecord) -> list[EvidencePackRecord]:
        async with self._lock:
            return list(self._evidence_packs.get(agent.id, []))

    async def start(
        self,
        *,
        agent: AgentRecord,
        change_package: ChangePackageRecord,
        body: DeploymentStart,
    ) -> tuple[DeploymentRecord, EvidencePackRecord]:
        if change_package.status not in {"approved", "deployable", "deployed"}:
            raise WorkspaceError(f"change package {change_package.id} is not approved for rollout")
        async with self._lock:
            now = datetime.now(UTC)
            deployment_id = f"dep_{uuid4().hex[:12]}"
            evidence_pack_id = f"ep_{uuid4().hex[:12]}"
            version_id = body.version_id or change_package.to_version_id
            traffic_percent = 0 if body.stage == "shadow" else body.traffic_percent
            deployment = DeploymentRecord(
                id=deployment_id,
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                version_id=version_id,
                change_package_id=change_package.id,
                evidence_pack_id=evidence_pack_id,
                stage=body.stage,
                status=body.stage,
                traffic_percent=traffic_percent,
                channel_scope=body.channel_scope,
                region_scope=body.region_scope,
                segment_scope=body.segment_scope,
                hold_time_minutes=body.hold_time_minutes,
                auto_rollback_thresholds=body.auto_rollback_thresholds,
                created_at=now,
                notes=body.notes,
            )
            evidence_pack = EvidencePackRecord(
                id=evidence_pack_id,
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                version_id=version_id,
                deployment_id=deployment_id,
                change_package_id=change_package.id,
                version_manifest={
                    "from_version_id": change_package.from_version_id,
                    "to_version_id": change_package.to_version_id,
                    "commitment_document_id": change_package.commitment_document_id,
                    "commitment_document_version": change_package.commitment_document_version,
                    "content_hash": change_package.content_hash,
                },
                behavior_diff_ref="change_package.semantic_diff",
                tool_permission_diff_ref="change_package.tool_changes",
                knowledge_diff_ref="change_package.knowledge_changes",
                memory_policy_ref="change_package.memory_changes",
                channel_deployment_plan_ref="deployment.channel_scope",
                eval_results_ref=change_package.eval_results_ref,
                approval_records_ref="change_package.required_approvals",
                canary_results_ref=f"deployment/{deployment_id}/{body.stage}",
                rollback_plan_ref=change_package.rollback_target_version_id,
                audit_log_ref=f"audit/change_package/{change_package.id}",
                created_at=now,
                export_formats=["pdf", "json", "csv", "grc_integration", "api"],
            )
            deployments = self._deployments.setdefault(agent.id, [])
            deployments.insert(0, deployment)
            self._evidence_packs.setdefault(agent.id, []).insert(0, evidence_pack)
            return deployment, evidence_pack

    async def action(
        self,
        *,
        agent: AgentRecord,
        deployment_id: str,
        action: Literal["promote", "pause", "rollback"],
    ) -> DeploymentRecord:
        async with self._lock:
            deployments = self._deployments.get(agent.id, [])
            for index, deployment in enumerate(deployments):
                if deployment.id != deployment_id:
                    continue
                now = datetime.now(UTC)
                if action == "promote":
                    updated = deployment.model_copy(
                        update={
                            "stage": "production",
                            "status": "live",
                            "traffic_percent": 100,
                            "promoted_at": now,
                            "paused_at": None,
                        }
                    )
                    for other_index, other in enumerate(deployments):
                        if other.id != deployment_id and other.status == "live":
                            deployments[other_index] = other.model_copy(
                                update={
                                    "status": "superseded",
                                    "traffic_percent": 0,
                                }
                            )
                elif action == "pause":
                    updated = deployment.model_copy(
                        update={"stage": "paused", "status": "paused", "paused_at": now}
                    )
                else:
                    updated = deployment.model_copy(
                        update={
                            "stage": "rolled_back",
                            "status": "rolled_back",
                            "traffic_percent": 0,
                            "rolled_back_at": now,
                        }
                    )
                    previous_live = next(
                        (item for item in deployments if item.status == "superseded"),
                        None,
                    )
                    if previous_live is not None:
                        previous_index = deployments.index(previous_live)
                        deployments[previous_index] = previous_live.model_copy(
                            update={"status": "live", "traffic_percent": 100}
                        )
                deployments[index] = updated
                return updated
        raise WorkspaceError(f"unknown deployment: {deployment_id}")


def deployment_payload(record: DeploymentRecord) -> dict[str, Any]:
    return _deployment_payload(record)


def evidence_pack_payload(record: EvidencePackRecord) -> dict[str, Any]:
    return _evidence_payload(record)
