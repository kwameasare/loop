from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.change_packages import (
    ChangePackageApprovalAction,
    ChangePackageGenerate,
    change_package_payload,
)

router = APIRouter(prefix="/v1/agents", tags=["ChangePackages"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    workspace_id: UUID,
    caller_sub: str,
) -> Any:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
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
        resource_type="change_package",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/change-packages")
async def list_change_packages(
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
    items = await request.app.state.cp.change_packages.list_for_agent(agent=agent)
    return {"items": [change_package_payload(item) for item in items]}


@router.get("/{agent_id}/change-packages/current")
async def get_current_change_package(
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
    current = await request.app.state.cp.change_packages.current(agent=agent)
    return {"item": change_package_payload(current) if current is not None else None}


@router.post("/{agent_id}/change-packages/preflight", status_code=201)
async def generate_change_package(
    request: Request,
    agent_id: UUID,
    body: ChangePackageGenerate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    package = await request.app.state.cp.change_packages.generate(
        agent=agent,
        commitment=commitment,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="change_package:generate",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "content_hash": package.content_hash,
            "commitment_document_id": package.commitment_document_id,
            "status": package.status,
        },
    )
    return change_package_payload(package)


@router.post("/{agent_id}/change-packages/{package_id}/submit")
async def submit_change_package(
    request: Request,
    agent_id: UUID,
    package_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    package = await request.app.state.cp.change_packages.submit(
        agent=agent,
        package_id=package_id,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="change_package:submit",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "content_hash": package.content_hash,
            "status": package.status,
        },
    )
    return change_package_payload(package)


@router.post("/{agent_id}/change-packages/{package_id}/approvals")
async def record_change_package_approval(
    request: Request,
    agent_id: UUID,
    package_id: str,
    body: ChangePackageApprovalAction,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    package = await request.app.state.cp.change_packages.record_approval(
        agent=agent,
        package_id=package_id,
        action=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="change_package:approval",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "approval_id": body.approval_id,
            "decision": body.decision,
            "content_hash": package.content_hash,
            "status": package.status,
        },
    )
    return change_package_payload(package)
