from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import EvalCaseCreate
from loop_control_plane.incidents import (
    IncidentCreate,
    IncidentStatus,
    IncidentTransition,
    incident_payload,
)

router_agents = APIRouter(prefix="/v1/agents", tags=["Incidents"])
router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Incidents"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    workspace_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> Any:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return await request.app.state.cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
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
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    incidents = await request.app.state.cp.incidents.list_for_workspace(
        workspace_id=workspace_id,
        agent_id=agent.id,
    )
    return {"items": [incident_payload(incident) for incident in incidents]}


@router_agents.post("/{agent_id}/incidents/anomaly", status_code=201)
async def create_incident_from_anomaly(
    request: Request,
    agent_id: UUID,
    body: IncidentCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
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
    workspace_id: UUID,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
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
    workspace_id: UUID = ACTIVE_WORKSPACE,
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
    workspace_id: UUID = ACTIVE_WORKSPACE,
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


@router_agents.post("/{agent_id}/incidents/{incident_id}/eval-cases", status_code=201)
async def seed_incident_eval_cases(
    request: Request,
    agent_id: UUID,
    incident_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
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
