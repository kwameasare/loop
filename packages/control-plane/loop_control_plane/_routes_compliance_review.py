from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.compliance_review import (
    ComplianceEvidenceExportCreate,
    build_compliance_review_payload,
    build_evidence_export_payload,
)

router = APIRouter(prefix="/v1/workspaces", tags=["ComplianceReview"])


async def _review_payload(
    request: Request,
    *,
    workspace_id: UUID,
    agent_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agents = await cp.agents.list_for_workspace(workspace_id)
    if agent_id is not None:
        agents = [agent for agent in agents if agent.id == agent_id]

    change_packages_by_agent = {
        agent.id: await cp.change_packages.list_for_agent(agent=agent) for agent in agents
    }
    tool_contracts_by_agent = {
        agent.id: await cp.tool_contracts.list_for_agent(agent=agent) for agent in agents
    }
    memory_policies_by_agent = {
        agent.id: await cp.memory_policies.list_for_agent(agent=agent) for agent in agents
    }
    channel_bindings_by_agent = {
        agent.id: await cp.channel_bindings.list_for_agent(agent=agent) for agent in agents
    }
    incidents = await cp.incidents.list_for_workspace(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    audit_events = cp.audit_events.list_for_workspace(workspace_id)
    return build_compliance_review_payload(
        workspace_id=workspace_id,
        agents=agents,
        change_packages_by_agent=change_packages_by_agent,
        tool_contracts_by_agent=tool_contracts_by_agent,
        memory_policies_by_agent=memory_policies_by_agent,
        channel_bindings_by_agent=channel_bindings_by_agent,
        incidents=incidents,
        audit_events=audit_events,
    )


@router.get("/{workspace_id}/compliance-review")
async def get_compliance_review(
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
    return await _review_payload(
        request,
        workspace_id=workspace_id,
        agent_id=agent_id,
    )


@router.post("/{workspace_id}/compliance-review/evidence-export", status_code=201)
async def create_compliance_evidence_export(
    request: Request,
    workspace_id: UUID,
    body: ComplianceEvidenceExportCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    review = await _review_payload(
        request,
        workspace_id=workspace_id,
        agent_id=body.agent_id,
    )
    cp = request.app.state.cp
    agents = await cp.agents.list_for_workspace(workspace_id)
    if body.agent_id is not None:
        agents = [agent for agent in agents if agent.id == body.agent_id]
    evidence_packs_by_agent = {
        agent.id: await cp.deployments.list_evidence_packs(agent=agent) for agent in agents
    }
    export = build_evidence_export_payload(
        workspace_id=workspace_id,
        body=body,
        review=review,
        evidence_packs_by_agent=evidence_packs_by_agent,
        actor_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="compliance:evidence_export",
        resource_type="compliance_evidence_export",
        resource_id=export["id"],
        store=cp.audit_events,
        request_id=request_id(request),
        payload={
            "agent_id": str(body.agent_id) if body.agent_id else None,
            "format": body.format,
            "sections": export["sections"],
            "artifact_count": len(export["artifact_refs"]),
        },
    )
    return export
