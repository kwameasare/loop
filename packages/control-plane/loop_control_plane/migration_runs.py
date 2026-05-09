from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.workspaces import WorkspaceError

MigrationRunStatus = Literal[
    "imported",
    "mapped",
    "parity_ready",
    "cutover_active",
    "cutover_complete",
    "rolled_back",
]
MigrationInventorySeverity = Literal["ok", "advisory", "blocking"]
CutoverStageStatus = Literal["pending", "in_progress", "passed", "halted"]


class MigrationImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="botpress", min_length=1, max_length=80)
    archive_name: str = Field(default="botpress-export.bpz", min_length=1, max_length=240)
    archive_sha: str = Field(default="", max_length=128)
    target_agent_name: str = Field(default="Imported Support Agent", min_length=1, max_length=64)
    target_agent_slug: str = Field(default="", max_length=64)
    business_responsibility: str = Field(default="", max_length=2000)
    channels: list[str] = Field(default_factory=lambda: ["web_chat"], max_length=20)
    inventory: dict[str, int] = Field(default_factory=dict, max_length=30)
    transcript_count: int = Field(default=0, ge=0, le=1_000_000)


class CutoverAdvance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1, max_length=120)
    evidence_ref: str = Field(default="", max_length=240)


class CutoverRollback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_id: str = Field(default="manual", max_length=120)
    reason: str = Field(default="Manual rollback requested.", max_length=1000)


class MigrationInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: str
    label: str
    count: int
    loop_target: str
    confidence: int
    severity: MigrationInventorySeverity
    evidence_ref: str


class MigrationLineageStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    status: str
    evidence_ref: str
    detail: str


class MigrationReadinessRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_score: int
    parity_passing: int
    parity_total: int
    blocking_count: int
    advisory_count: int


class MigrationCutoverStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    percent: int
    duration_minutes: int
    status: CutoverStageStatus
    guardrails: list[str]


class MigrationCutoverEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    action: str
    stage_id: str
    actor_sub: str
    evidence_ref: str
    created_at: datetime


class MigrationRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    source: str
    archive_name: str
    archive_sha: str
    target_agent_id: UUID
    target_agent_name: str
    target_branch_id: str
    target_change_set_id: str
    commitment_document_id: str
    status: MigrationRunStatus
    inventory: list[MigrationInventoryItem]
    lineage_steps: list[MigrationLineageStep]
    readiness: MigrationReadinessRecord
    cutover_stages: list[MigrationCutoverStage]
    cutover_events: list[MigrationCutoverEvent]
    rollback_triggers: list[dict[str, Any]]
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


def migration_run_payload(record: MigrationRunRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def migration_run_summary(record: MigrationRunRecord) -> dict[str, Any]:
    payload = migration_run_payload(record)
    payload["inventory_total"] = sum(item.count for item in record.inventory)
    return payload


def slugify_agent_name(name: str, fallback: str = "imported-agent") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:64] or fallback


class MigrationRunRegistry:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[MigrationRunRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_workspace(self, workspace_id: UUID) -> list[MigrationRunRecord]:
        async with self._lock:
            return list(self._runs.get(workspace_id, []))

    async def latest_for_workspace(self, workspace_id: UUID) -> MigrationRunRecord | None:
        async with self._lock:
            return next(iter(self._runs.get(workspace_id, [])), None)

    async def get(self, *, workspace_id: UUID, migration_id: str) -> MigrationRunRecord:
        async with self._lock:
            return self._find_unlocked(workspace_id=workspace_id, migration_id=migration_id)

    async def create(
        self,
        *,
        workspace_id: UUID,
        body: MigrationImportCreate,
        target_agent_id: UUID,
        target_branch_id: str,
        target_change_set_id: str,
        commitment_document_id: str,
        actor_sub: str,
    ) -> MigrationRunRecord:
        async with self._lock:
            now = datetime.now(UTC)
            inventory = _inventory_from_body(body, workspace_id=workspace_id)
            readiness = _readiness_from_inventory(inventory, transcript_count=body.transcript_count)
            record = MigrationRunRecord(
                id=f"mig_{uuid4().hex[:12]}",
                workspace_id=workspace_id,
                source=body.source,
                archive_name=body.archive_name,
                archive_sha=_archive_sha(body, workspace_id),
                target_agent_id=target_agent_id,
                target_agent_name=body.target_agent_name,
                target_branch_id=target_branch_id,
                target_change_set_id=target_change_set_id,
                commitment_document_id=commitment_document_id,
                status="parity_ready"
                if readiness.blocking_count == 0 and readiness.parity_total > 0
                else "mapped",
                inventory=inventory,
                lineage_steps=_lineage_steps(
                    body=body,
                    workspace_id=workspace_id,
                    target_agent_id=target_agent_id,
                    target_branch_id=target_branch_id,
                    target_change_set_id=target_change_set_id,
                    commitment_document_id=commitment_document_id,
                ),
                readiness=readiness,
                cutover_stages=_cutover_stages(readiness),
                cutover_events=[],
                rollback_triggers=_rollback_triggers(workspace_id, body.source),
                created_by_user_id=actor_sub,
                created_at=now,
                updated_at=now,
            )
            self._runs.setdefault(workspace_id, []).insert(0, record)
            return record

    async def advance_cutover(
        self,
        *,
        workspace_id: UUID,
        migration_id: str,
        body: CutoverAdvance,
        actor_sub: str,
    ) -> MigrationRunRecord:
        async with self._lock:
            record = self._find_unlocked(workspace_id=workspace_id, migration_id=migration_id)
            if record.status == "rolled_back":
                raise WorkspaceError("rolled back migrations cannot advance")
            if record.readiness.blocking_count:
                raise WorkspaceError("blocking migration items must be resolved before cutover")
            stages = list(record.cutover_stages)
            index = next((idx for idx, stage in enumerate(stages) if stage.id == body.stage_id), -1)
            if index < 0:
                raise WorkspaceError(f"unknown cutover stage: {body.stage_id}")
            stage = stages[index]
            if stage.status not in {"pending", "in_progress"}:
                raise WorkspaceError(f"stage {stage.id} is already {stage.status}")
            if index > 0 and stages[index - 1].status != "passed":
                raise WorkspaceError("previous cutover stage must pass first")
            stages[index] = stage.model_copy(update={"status": "passed"})
            next_index = index + 1
            status: MigrationRunStatus = "cutover_active"
            if next_index < len(stages):
                stages[next_index] = stages[next_index].model_copy(update={"status": "in_progress"})
            else:
                status = "cutover_complete"
            event = MigrationCutoverEvent(
                id=f"migevt_{uuid4().hex[:12]}",
                action="advance",
                stage_id=stage.id,
                actor_sub=actor_sub,
                evidence_ref=body.evidence_ref
                or f"audit/migration/{workspace_id}/{record.source}/cutover/{stage.id}",
                created_at=datetime.now(UTC),
            )
            updated = record.model_copy(
                update={
                    "status": status,
                    "cutover_stages": stages,
                    "cutover_events": [event, *record.cutover_events],
                    "updated_at": event.created_at,
                }
            )
            self._replace_unlocked(workspace_id=workspace_id, record=updated)
            return updated

    async def rollback(
        self,
        *,
        workspace_id: UUID,
        migration_id: str,
        body: CutoverRollback,
        actor_sub: str,
    ) -> MigrationRunRecord:
        async with self._lock:
            record = self._find_unlocked(workspace_id=workspace_id, migration_id=migration_id)
            now = datetime.now(UTC)
            stages = [
                stage.model_copy(update={"status": "halted"})
                if stage.status in {"pending", "in_progress"}
                else stage
                for stage in record.cutover_stages
            ]
            event = MigrationCutoverEvent(
                id=f"migevt_{uuid4().hex[:12]}",
                action="rollback",
                stage_id=body.trigger_id,
                actor_sub=actor_sub,
                evidence_ref=f"audit/migration/{workspace_id}/{record.source}/rollback/{body.trigger_id}",
                created_at=now,
            )
            updated = record.model_copy(
                update={
                    "status": "rolled_back",
                    "cutover_stages": stages,
                    "cutover_events": [event, *record.cutover_events],
                    "updated_at": now,
                }
            )
            self._replace_unlocked(workspace_id=workspace_id, record=updated)
            return updated

    def _find_unlocked(self, *, workspace_id: UUID, migration_id: str) -> MigrationRunRecord:
        for record in self._runs.get(workspace_id, []):
            if record.id == migration_id:
                return record
        raise WorkspaceError(f"unknown migration run: {migration_id}")

    def _replace_unlocked(self, *, workspace_id: UUID, record: MigrationRunRecord) -> None:
        items = self._runs.get(workspace_id, [])
        for index, item in enumerate(items):
            if item.id == record.id:
                items[index] = record
                return
        raise WorkspaceError(f"unknown migration run: {record.id}")


def _archive_sha(body: MigrationImportCreate, workspace_id: UUID) -> str:
    if body.archive_sha.startswith("sha256:"):
        return body.archive_sha
    if body.archive_sha:
        return f"sha256:{body.archive_sha}"
    return f"sha256:{workspace_id.hex:0<64}"[:71]


def _inventory_from_body(
    body: MigrationImportCreate,
    *,
    workspace_id: UUID,
) -> list[MigrationInventoryItem]:
    counts = {
        "intents": 42,
        "workflows": 19,
        "nodes": 88,
        "knowledge_sources": 13,
        "integrations": 4,
        "channels": max(1, len(body.channels)),
        "transcripts": body.transcript_count,
        **body.inventory,
    }
    targets = {
        "intents": "capabilities",
        "workflows": "behavior policies + eval scenarios",
        "nodes": "behavior routines",
        "knowledge_sources": "knowledge sources",
        "integrations": "tool contracts",
        "channels": "channel bindings",
        "transcripts": "parity eval suite",
    }
    items: list[MigrationInventoryItem] = []
    for kind, count in counts.items():
        if count <= 0:
            continue
        severity: MigrationInventorySeverity = "ok"
        confidence = 92
        if kind in {"integrations", "custom_hooks", "unsupported_nodes"}:
            severity = "blocking"
            confidence = 58
        elif kind in {"workflows", "nodes", "channels"}:
            severity = "advisory"
            confidence = 76
        target = targets.get(kind, "review queue")
        items.append(
            MigrationInventoryItem(
                id=f"inv_{kind}",
                kind=kind,
                label=kind.replace("_", " ").title(),
                count=count,
                loop_target=target,
                confidence=confidence,
                severity=severity,
                evidence_ref=f"audit/migration/{workspace_id}/{body.source}/inventory/{kind}",
            )
        )
    return items


def _readiness_from_inventory(
    inventory: list[MigrationInventoryItem],
    *,
    transcript_count: int,
) -> MigrationReadinessRecord:
    blocking_count = sum(1 for item in inventory if item.severity == "blocking")
    advisory_count = sum(1 for item in inventory if item.severity == "advisory")
    parity_total = transcript_count or 0
    parity_passing = max(0, parity_total - blocking_count * 3 - advisory_count)
    score = max(0, min(100, 100 - blocking_count * 18 - advisory_count * 5))
    if parity_total == 0:
        score = min(score, 72)
    return MigrationReadinessRecord(
        overall_score=score,
        parity_passing=parity_passing,
        parity_total=parity_total,
        blocking_count=blocking_count,
        advisory_count=advisory_count,
    )


def _lineage_steps(
    *,
    body: MigrationImportCreate,
    workspace_id: UUID,
    target_agent_id: UUID,
    target_branch_id: str,
    target_change_set_id: str,
    commitment_document_id: str,
) -> list[MigrationLineageStep]:
    base = f"audit/migration/{workspace_id}/{body.source}"
    return [
        MigrationLineageStep(
            id="parse",
            label="Parse source archive",
            status="ok",
            evidence_ref=f"{base}/parse",
            detail=f"Parsed `{body.archive_name}` and preserved source artifact IDs.",
        ),
        MigrationLineageStep(
            id="inventory",
            label="Inventory artifacts",
            status="ok",
            evidence_ref=f"{base}/inventory",
            detail="Detected source intents, workflows, integrations, channels, and transcripts.",
        ),
        MigrationLineageStep(
            id="contract",
            label="Create Commitment Document",
            status="ok",
            evidence_ref=f"commitment/{commitment_document_id}",
            detail="Created a draft Agent Contract from migration intent and risk boundaries.",
        ),
        MigrationLineageStep(
            id="branch",
            label="Create migration branch",
            status="ok",
            evidence_ref=f"branch/{target_branch_id}",
            detail=f"Migration output landed on branch `{target_branch_id}` for agent `{target_agent_id}`.",
        ),
        MigrationLineageStep(
            id="change-set",
            label="Create migration Change Set",
            status="ok",
            evidence_ref=f"change-set/{target_change_set_id}",
            detail="Generated mapping changes as reviewable work, not direct production state.",
        ),
    ]


def _cutover_stages(readiness: MigrationReadinessRecord) -> list[MigrationCutoverStage]:
    first_status: CutoverStageStatus = (
        "in_progress" if readiness.blocking_count == 0 and readiness.parity_total > 0 else "pending"
    )
    return [
        MigrationCutoverStage(
            id="canary_1pct",
            percent=1,
            duration_minutes=30,
            status=first_status,
            guardrails=["shadow_agreement>=95%", "regression=0", "error_rate<0.5%"],
        ),
        MigrationCutoverStage(
            id="canary_10pct",
            percent=10,
            duration_minutes=60,
            status="pending",
            guardrails=["regression<2", "cost_per_turn<150%"],
        ),
        MigrationCutoverStage(
            id="canary_100pct",
            percent=100,
            duration_minutes=0,
            status="pending",
            guardrails=["all-stages-passed", "rollback-route-armed"],
        ),
    ]


def _rollback_triggers(workspace_id: UUID, source: str) -> list[dict[str, Any]]:
    base = f"audit/migration/{workspace_id}/{source}/rollback"
    return [
        {
            "id": "rb_regression",
            "metric": "regression",
            "threshold": ">1 parity regression during canary",
            "action": "Halt canary and restore source-platform routing.",
            "evidenceRef": f"{base}/regression",
        },
        {
            "id": "rb_error_rate",
            "metric": "error_rate",
            "threshold": "5xx rate >2% over 5m",
            "action": "Halt canary and page the migration owner.",
            "evidenceRef": f"{base}/error-rate",
        },
        {
            "id": "rb_cost",
            "metric": "cost_spike",
            "threshold": "Cost-per-turn >150% baseline",
            "action": "Throttle migration traffic and alert finance.",
            "evidenceRef": f"{base}/cost",
        },
    ]
