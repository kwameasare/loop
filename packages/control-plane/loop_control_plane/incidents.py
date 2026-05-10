from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentRecord
from loop_control_plane.workspaces import WorkspaceError

IncidentSeverity = Literal["low", "medium", "high", "critical"]
IncidentStatus = Literal[
    "open",
    "contained",
    "investigating",
    "fix_staged",
    "resolved",
    "archived",
]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deployment_id: str = Field(default="", max_length=160)
    severity: IncidentSeverity = "high"
    trigger: str = Field(min_length=1, max_length=500)
    affected_trace_ids: list[str] = Field(default_factory=list, max_length=100)
    affected_conversation_count: int = Field(default=0, ge=0)
    root_cause_hypothesis: str = Field(default="", max_length=2000)
    rollback_action_ref: str = Field(default="", max_length=240)
    proposed_fix: str = Field(default="", max_length=2000)
    status: IncidentStatus = "open"
    channel_scope: list[str] = Field(default_factory=list, max_length=20)
    notification_targets: list[str] = Field(default_factory=list, max_length=10)
    created_from: str = Field(default="manual", max_length=120)


class IncidentTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(default="", max_length=1200)


class IncidentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: UUID
    agent_id: UUID
    deployment_id: str
    severity: IncidentSeverity
    trigger: str
    status: IncidentStatus
    affected_trace_ids: list[str]
    affected_conversation_count: int
    root_cause_hypothesis: str
    rollback_action_ref: str
    proposed_fix: str
    candidate_eval_suite_id: str | None
    fix_change_package_id: str | None = None
    channel_scope: list[str]
    notifications: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    report: dict[str, Any]
    created_at: datetime
    created_by: str
    resolved_at: datetime | None = None


def _timeline_event(kind: str, at: datetime, summary: str) -> dict[str, str]:
    return {"kind": kind, "at": at.isoformat(), "summary": summary}


def _notifications_for(body: IncidentCreate, now: datetime) -> list[dict[str, str]]:
    recipients = list(
        dict.fromkeys(target.strip() for target in body.notification_targets if target.strip())
    )
    return [
        {
            "recipient": recipient,
            "channel": "in_app",
            "status": "queued",
            "sent_at": now.isoformat(),
            "summary": f"{body.severity} incident: {body.trigger}",
        }
        for recipient in recipients
    ]


def _report_for(body: IncidentCreate, notifications: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "trigger": body.trigger,
        "affected_conversations": body.affected_conversation_count,
        "affected_channels": body.channel_scope,
        "customer_impact": (
            "Unknown until affected traces are reviewed."
            if body.affected_conversation_count == 0
            else f"{body.affected_conversation_count} conversations require review."
        ),
        "actions_taken": [body.rollback_action_ref] if body.rollback_action_ref else [],
        "suspected_cause": body.root_cause_hypothesis
        or "Pending trace and deployment-event review.",
        "proposed_fix": body.proposed_fix or "Generate candidate evals before fix.",
        "candidate_regression_tests": body.affected_trace_ids,
        "rollback_status": "executed" if body.rollback_action_ref else "not_started",
        "notifications": notifications,
    }


def incident_payload(record: IncidentRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


class IncidentRegistry:
    def __init__(self) -> None:
        self._incidents: dict[UUID, list[IncidentRecord]] = {}
        self._lock = asyncio.Lock()

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID | None = None,
    ) -> list[IncidentRecord]:
        async with self._lock:
            records = list(self._incidents.get(workspace_id, []))
        if agent_id is not None:
            records = [record for record in records if record.agent_id == agent_id]
        return records

    async def create(
        self,
        *,
        agent: AgentRecord,
        body: IncidentCreate,
        actor_sub: str,
    ) -> IncidentRecord:
        async with self._lock:
            now = datetime.now(UTC)
            notifications = _notifications_for(body, now)
            record = IncidentRecord(
                id=f"inc_{uuid4().hex[:12]}",
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                deployment_id=body.deployment_id,
                severity=body.severity,
                trigger=body.trigger,
                status=body.status,
                affected_trace_ids=body.affected_trace_ids,
                affected_conversation_count=body.affected_conversation_count,
                root_cause_hypothesis=body.root_cause_hypothesis,
                rollback_action_ref=body.rollback_action_ref,
                proposed_fix=body.proposed_fix,
                candidate_eval_suite_id=None,
                fix_change_package_id=None,
                channel_scope=body.channel_scope,
                notifications=notifications,
                timeline=[
                    _timeline_event(
                        "incident_created",
                        now,
                        f"Incident created from {body.created_from}.",
                    )
                ],
                report=_report_for(body, notifications),
                created_at=now,
                created_by=actor_sub,
            )
            self._incidents.setdefault(agent.workspace_id, []).insert(0, record)
            return record

    async def create_for_rollback(
        self,
        *,
        agent: AgentRecord,
        deployment_id: str,
        version_id: str,
        actor_sub: str,
        mode: Literal["manual", "auto"] = "manual",
        trigger: str = "",
        reason: str = "",
        affected_trace_ids: list[str] | None = None,
        notification_targets: list[str] | None = None,
    ) -> IncidentRecord:
        label = "auto-rollback" if mode == "auto" else "manual rollback"
        trace_ids = affected_trace_ids or []
        body = IncidentCreate(
            deployment_id=deployment_id,
            severity="high" if mode == "auto" else "medium",
            trigger=trigger or f"{label} executed for deployment {deployment_id}",
            affected_trace_ids=trace_ids,
            affected_conversation_count=len(trace_ids),
            root_cause_hypothesis=reason or "Rollback executed before root cause was confirmed.",
            rollback_action_ref=f"deployment/{deployment_id}/rollback",
            proposed_fix=(
                f"Review traces around deployment {deployment_id}, seed incident "
                f"evals, then create a Change Package against {version_id}."
            ),
            status="contained",
            notification_targets=notification_targets or [],
            created_from=label.replace(" ", "_"),
        )
        record = await self.create(agent=agent, body=body, actor_sub=actor_sub)
        now = datetime.now(UTC)
        contained = record.model_copy(
            update={
                "timeline": [
                    *record.timeline,
                    *(
                        [
                            _timeline_event(
                                "affected_traces_collected",
                                now,
                                f"{len(trace_ids)} affected trace(s) attached to the incident report.",
                            )
                        ]
                        if trace_ids
                        else []
                    ),
                    _timeline_event(
                        "containment",
                        now,
                        f"{label.capitalize()} moved traffic away from {version_id}.",
                    ),
                ]
            }
        )
        await self._replace(contained)
        return contained

    async def get(self, *, agent: AgentRecord, incident_id: str) -> IncidentRecord:
        async with self._lock:
            for record in self._incidents.get(agent.workspace_id, []):
                if record.agent_id == agent.id and record.id == incident_id:
                    return record
        raise WorkspaceError(f"unknown incident: {incident_id}")

    async def transition(
        self,
        *,
        agent: AgentRecord,
        incident_id: str,
        status: IncidentStatus,
        note: str,
    ) -> IncidentRecord:
        record = await self.get(agent=agent, incident_id=incident_id)
        now = datetime.now(UTC)
        updated = record.model_copy(
            update={
                "status": status,
                "resolved_at": now if status == "resolved" else record.resolved_at,
                "timeline": [
                    *record.timeline,
                    _timeline_event(
                        status,
                        now,
                        note or f"Incident moved to {status}.",
                    ),
                ],
            }
        )
        await self._replace(updated)
        return updated

    async def link_eval_suite(
        self,
        *,
        agent: AgentRecord,
        incident_id: str,
        suite_id: str,
    ) -> IncidentRecord:
        record = await self.get(agent=agent, incident_id=incident_id)
        now = datetime.now(UTC)
        updated = record.model_copy(
            update={
                "candidate_eval_suite_id": suite_id,
                "timeline": [
                    *record.timeline,
                    _timeline_event(
                        "evals_seeded",
                        now,
                        f"Candidate regression evals added to suite {suite_id}.",
                    ),
                ],
                "report": {
                    **record.report,
                    "candidate_eval_suite_id": suite_id,
                },
            }
        )
        await self._replace(updated)
        return updated

    async def link_fix_change_package(
        self,
        *,
        agent: AgentRecord,
        incident_id: str,
        package_id: str,
    ) -> IncidentRecord:
        record = await self.get(agent=agent, incident_id=incident_id)
        now = datetime.now(UTC)
        updated = record.model_copy(
            update={
                "status": "fix_staged",
                "fix_change_package_id": package_id,
                "timeline": [
                    *record.timeline,
                    _timeline_event(
                        "fix_change_package_created",
                        now,
                        f"Fix Change Package {package_id} created from incident.",
                    ),
                ],
                "report": {
                    **record.report,
                    "fix_change_package_id": package_id,
                    "actions_taken": [
                        *record.report.get("actions_taken", []),
                        f"change_package/{package_id}",
                    ],
                },
            }
        )
        await self._replace(updated)
        return updated

    async def _replace(self, updated: IncidentRecord) -> None:
        async with self._lock:
            records = self._incidents.get(updated.workspace_id, [])
            for index, record in enumerate(records):
                if record.id == updated.id:
                    records[index] = updated
                    return
            raise WorkspaceError(f"unknown incident: {updated.id}")
