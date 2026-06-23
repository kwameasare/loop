from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._agent_route_utils import resolve_agent_for_route
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.change_packages import (
    ChangePackageGenerate,
    change_package_payload,
    infer_change_risk,
    infer_change_types,
)
from loop_control_plane.eval_suites import EvalCaseCreate
from loop_control_plane.incidents import (
    IncidentCreate,
    IncidentStatus,
    IncidentTransition,
    incident_payload,
)
from loop_control_plane.preapproved_classes import RiskCeiling, preapproved_class_payload

router_agents = APIRouter(prefix="/v1/agents", tags=["Incidents"])
router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Incidents"])


class IncidentFixPackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: str = Field(default="incident/fix", max_length=160)
    change_set_id: str = Field(default="", max_length=160)
    release_candidate_id: str = Field(default="", max_length=160)
    from_version_id: str = Field(default="production", max_length=160)
    to_version_id: str = Field(default="draft-incident-fix", max_length=160)
    target_environment: str = Field(default="production", max_length=64)
    summary: str = Field(default="", max_length=2000)


def _fix_package_body(incident: Any, body: IncidentFixPackageCreate) -> ChangePackageGenerate:
    trace_refs = incident.affected_trace_ids or [f"incident/{incident.id}"]
    first_trace = trace_refs[0]
    summary = body.summary or f"Fix incident {incident.id}: {incident.trigger}"
    proposed_fix = incident.proposed_fix or "Review affected traces and stage a minimal fix."
    root_cause = (
        incident.root_cause_hypothesis or "Root cause is pending trace and deployment-event review."
    )
    return ChangePackageGenerate(
        branch_id=body.branch_id,
        change_set_id=body.change_set_id or f"incident-{incident.id}",
        release_candidate_id=body.release_candidate_id or f"rc-{incident.id}",
        from_version_id=body.from_version_id,
        to_version_id=body.to_version_id,
        target_environment=body.target_environment,
        summary=summary,
        semantic_diff=[
            {
                "dimension": "incident",
                "summary": proposed_fix,
                "evidence_ref": f"incident/{incident.id}",
            },
            {
                "dimension": "behavior",
                "summary": root_cause,
                "evidence_ref": f"trace/{first_trace}",
            },
        ],
        eval_results_ref=incident.candidate_eval_suite_id
        or f"incident/{incident.id}/candidate-evals",
        replay_results_ref=f"incident/{incident.id}/affected-traces",
        risk_summary=(
            f"{incident.severity} incident fix for {incident.affected_conversation_count} "
            "affected conversation(s)."
        ),
        cost_summary="No cost claim accepted until incident replay runs on the fix draft.",
        latency_summary="No latency claim accepted until affected traces replay on the fix draft.",
        channel_readiness_summary=(
            "Incident channel scope: "
            + (", ".join(incident.channel_scope) if incident.channel_scope else "all channels")
        ),
        rollback_target_version_id=incident.rollback_action_ref or "last-known-safe",
    )


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    return await resolve_agent_for_route(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=required_role,
    )


async def _notification_targets(request: Request, *, agent: Any, fallback: str) -> list[str]:
    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    return list(
        dict.fromkeys(
            target
            for target in (
                commitment.body.owner_user_id.strip(),
                commitment.body.backup_owner_user_id.strip(),
                fallback,
            )
            if target
        )
    )


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_id: str,
    payload: object | None = None,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type="incident",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


async def _expire_preapproved_classes(
    request: Request,
    *,
    agent: Any,
    caller_sub: str,
    trigger: str,
) -> None:
    expired = await request.app.state.cp.preapproved_classes.expire_for_agent(
        agent=agent
    )
    for record in expired:
        record_audit_event(
            workspace_id=agent.workspace_id,
            actor_sub=caller_sub,
            action="pre_approved_class:expire",
            resource_type="pre_approved_class",
            resource_id=record.id,
            store=request.app.state.cp.audit_events,
            request_id=request_id(request),
            payload={
                "agent_id": str(agent.id),
                "expires_at": record.expires_at.isoformat(),
                "expired_at": record.expired_at.isoformat()
                if record.expired_at
                else None,
                "revoked_at": record.revoked_at.isoformat()
                if record.revoked_at
                else None,
                "trigger": trigger,
            },
        )


@router_workspaces.get("/{workspace_id}/incidents")
async def list_workspace_incidents(
    request: Request,
    workspace_id: UUID,
    agent_id: UUID | None = None,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    incidents = await request.app.state.cp.incidents.list_for_workspace(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    return {"items": [incident_payload(incident) for incident in incidents]}


@router_agents.get("/{agent_id}/incidents")
async def list_agent_incidents(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    incidents = await request.app.state.cp.incidents.list_for_workspace(
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
    )
    return {"items": [incident_payload(incident) for incident in incidents]}


@router_agents.post("/{agent_id}/incidents/anomaly", status_code=201)
async def create_incident_from_anomaly(
    request: Request,
    agent_id: UUID,
    body: IncidentCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    if not body.notification_targets:
        body = body.model_copy(
            update={
                "notification_targets": await _notification_targets(
                    request,
                    agent=agent,
                    fallback=caller_sub,
                )
            }
        )
    incident = await request.app.state.cp.incidents.create(
        agent=agent,
        body=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="incident:create",
        resource_id=incident.id,
        payload={
            "agent_id": str(agent_id),
            "deployment_id": incident.deployment_id,
            "severity": incident.severity,
            "trigger": incident.trigger,
            "notification_targets": [item["recipient"] for item in incident.notifications],
        },
    )
    return incident_payload(incident)


async def _transition(
    request: Request,
    *,
    agent_id: UUID,
    incident_id: str,
    status: IncidentStatus,
    body: IncidentTransition,
    caller_sub: str,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    incident = await request.app.state.cp.incidents.transition(
        agent=agent,
        incident_id=incident_id,
        status=status,
        note=body.note,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action=f"incident:{status}",
        resource_id=incident.id,
        payload={"agent_id": str(agent_id), "status": incident.status},
    )
    return incident_payload(incident)


@router_agents.post("/{agent_id}/incidents/{incident_id}/contain")
async def contain_incident(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    body: IncidentTransition,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _transition(
        request,
        agent_id=agent_id,
        incident_id=incident_id,
        status="contained",
        body=body,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router_agents.post("/{agent_id}/incidents/{incident_id}/resolve")
async def resolve_incident(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    body: IncidentTransition,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _transition(
        request,
        agent_id=agent_id,
        incident_id=incident_id,
        status="resolved",
        body=body,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router_agents.post("/{agent_id}/incidents/{incident_id}/investigate")
async def investigate_incident(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    body: IncidentTransition,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _transition(
        request,
        agent_id=agent_id,
        incident_id=incident_id,
        status="investigating",
        body=body,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router_agents.post("/{agent_id}/incidents/{incident_id}/archive")
async def archive_incident(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    body: IncidentTransition,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    return await _transition(
        request,
        agent_id=agent_id,
        incident_id=incident_id,
        status="archived",
        body=body,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router_agents.post("/{agent_id}/incidents/{incident_id}/eval-cases", status_code=201)
async def seed_incident_eval_cases(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    incident = await request.app.state.cp.incidents.get(
        agent=agent,
        incident_id=incident_id,
    )
    suite = await request.app.state.cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name="Incident regressions",
        dataset_ref="incident-regressions",
        metrics=["incident_regression", "groundedness", "rollback_safety"],
        actor_sub=caller_sub,
    )
    trace_ids = incident.affected_trace_ids or [f"incident/{incident.id}"]
    case_ids: list[str] = []
    for trace_id in trace_ids:
        case = await request.app.state.cp.eval_suites.add_case(
            workspace_id=workspace_id,
            suite_id=suite.id,
            body=EvalCaseCreate(
                name=f"{incident.trigger} regression",
                input={
                    "incident_id": incident.id,
                    "agent_id": str(agent_id),
                    "trace_id": trace_id,
                    "trigger": incident.trigger,
                    "rollback_action_ref": incident.rollback_action_ref,
                },
                expected={
                    "outcome": incident.proposed_fix,
                    "root_cause_hypothesis": incident.root_cause_hypothesis,
                },
                scorers=[
                    {
                        "kind": "llm_judge",
                        "config": {"rubric": "incident regression expected behavior"},
                    },
                    {
                        "kind": "trace_regression",
                        "config": {"trace_id": trace_id},
                    },
                ],
                source="incident",
                source_ref=incident.id,
                attachments=[incident.id, trace_id],
            ),
            actor_sub=caller_sub,
        )
        case_ids.append(str(case.id))
    updated = await request.app.state.cp.incidents.link_eval_suite(
        agent=agent,
        incident_id=incident.id,
        suite_id=str(suite.id),
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="incident:eval_cases_seeded",
        resource_id=incident.id,
        payload={
            "agent_id": str(agent_id),
            "suite_id": str(suite.id),
            "case_ids": case_ids,
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_ids": case_ids,
        "incident": incident_payload(updated),
    }


@router_agents.post("/{agent_id}/incidents/{incident_id}/change-package", status_code=201)
async def create_incident_fix_change_package(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    body: IncidentFixPackageCreate | None = None,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    incident = await request.app.state.cp.incidents.get(
        agent=agent,
        incident_id=incident_id,
    )
    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    generate_body = _fix_package_body(incident, body or IncidentFixPackageCreate())
    change_types = infer_change_types(generate_body)
    risk = infer_change_risk(generate_body)
    await _expire_preapproved_classes(
        request,
        agent=agent,
        caller_sub=caller_sub,
        trigger="incident_fix_preflight",
    )
    preapproved = await request.app.state.cp.preapproved_classes.applicable(
        agent=agent,
        change_types=change_types,
        risk=cast(RiskCeiling, risk),
        actor_sub=caller_sub,
    )
    package = await request.app.state.cp.change_packages.generate(
        agent=agent,
        commitment=commitment,
        body=generate_body,
        pre_approved_classes=[
            {
                **preapproved_class_payload(record),
                "matched_change_types": change_types,
                "matched_risk": risk,
            }
            for record in preapproved
        ],
    )
    await request.app.state.cp.preapproved_classes.mark_used(
        agent=agent,
        class_ids=[record.id for record in preapproved],
        package_id=package.id,
    )
    updated = await request.app.state.cp.incidents.link_fix_change_package(
        agent=agent,
        incident_id=incident.id,
        package_id=package.id,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="change_package:generate_from_incident",
        resource_type="change_package",
        resource_id=package.id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "incident_id": incident.id,
            "content_hash": package.content_hash,
            "change_types": change_types,
            "risk": risk,
            "pre_approved_classes": [record.id for record in preapproved],
        },
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="incident:fix_change_package_created",
        resource_id=incident.id,
        payload={
            "agent_id": str(agent_id),
            "change_package_id": package.id,
            "content_hash": package.content_hash,
        },
    )
    return {
        "ok": True,
        "change_package": change_package_payload(package),
        "incident": incident_payload(updated),
    }
