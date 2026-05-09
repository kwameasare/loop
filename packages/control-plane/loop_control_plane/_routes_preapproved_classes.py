from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.preapproved_classes import (
    PreApprovedClassCreate,
    preapproved_class_payload,
)

router = APIRouter(prefix="/v1/agents", tags=["PreApprovedClasses"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    workspace_id: UUID,
    caller_sub: str,
    admin: bool = False,
) -> Any:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN if admin else None,
    )
    return await request.app.state.cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
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
        resource_type="pre_approved_class",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/pre-approved-classes")
async def list_preapproved_classes(
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
    rows = await request.app.state.cp.preapproved_classes.list_for_agent(agent=agent)
    return {"items": [preapproved_class_payload(row) for row in rows]}


@router.post("/{agent_id}/pre-approved-classes", status_code=201)
async def create_preapproved_class(
    request: Request,
    agent_id: UUID,
    body: PreApprovedClassCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    record = await request.app.state.cp.preapproved_classes.create(
        agent=agent,
        body=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="pre_approved_class:create",
        resource_id=record.id,
        payload={
            "agent_id": str(agent.id),
            "granted_to_user_id": record.granted_to_user_id,
            "team_id": record.team_id,
            "allowed_change_types": record.allowed_change_types,
            "excluded_change_types": record.excluded_change_types,
            "risk_ceiling": record.risk_ceiling,
            "expires_at": record.expires_at.isoformat(),
        },
    )
    return preapproved_class_payload(record)


@router.post("/{agent_id}/pre-approved-classes/{class_id}/revoke")
async def revoke_preapproved_class(
    request: Request,
    agent_id: UUID,
    class_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    record = await request.app.state.cp.preapproved_classes.revoke(
        agent=agent,
        class_id=class_id,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="pre_approved_class:revoke",
        resource_id=record.id,
        payload={"agent_id": str(agent.id), "status": record.status},
    )
    return preapproved_class_payload(record)
