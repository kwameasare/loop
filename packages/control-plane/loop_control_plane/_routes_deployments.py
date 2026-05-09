from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.deployments import (
    DeploymentStart,
    deployment_payload,
    evidence_pack_payload,
)
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["Deployments"])


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


async def _change_package(request: Request, *, agent: Any, package_id: str) -> Any:
    packages = await request.app.state.cp.change_packages.list_for_agent(agent=agent)
    for package in packages:
        if package.id == package_id:
            return package
    raise WorkspaceError(f"unknown change package: {package_id}")


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
        resource_type="deployment",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/deployments")
async def list_deployments(
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
    deployments = await request.app.state.cp.deployments.list_for_agent(agent=agent)
    return {"items": [deployment_payload(deployment) for deployment in deployments]}


@router.post("/{agent_id}/deployments/start", status_code=201)
async def start_deployment(
    request: Request,
    agent_id: UUID,
    body: DeploymentStart,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    change_package = await _change_package(
        request,
        agent=agent,
        package_id=body.change_package_id,
    )
    deployment, evidence_pack = await request.app.state.cp.deployments.start(
        agent=agent,
        change_package=change_package,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="deployment:start",
        resource_id=deployment.id,
        payload={
            "agent_id": str(agent_id),
            "change_package_id": change_package.id,
            "evidence_pack_id": evidence_pack.id,
            "traffic_percent": deployment.traffic_percent,
            "channel_scope": deployment.channel_scope,
        },
    )
    return {
        "deployment": deployment_payload(deployment),
        "evidence_pack": evidence_pack_payload(evidence_pack),
    }


async def _deployment_action(
    request: Request,
    *,
    agent_id: UUID,
    deployment_id: str,
    action: str,
    caller_sub: str,
    workspace_id: UUID,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    deployment = await request.app.state.cp.deployments.action(
        agent=agent,
        deployment_id=deployment_id,
        action=action,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action=f"deployment:{action}",
        resource_id=deployment.id,
        payload={"agent_id": str(agent_id), "status": deployment.status},
    )
    return deployment_payload(deployment)


@router.post("/{agent_id}/deployments/{deployment_id}/promote")
async def promote_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="promote",
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.post("/{agent_id}/deployments/{deployment_id}/pause")
async def pause_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="pause",
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.post("/{agent_id}/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    request: Request,
    agent_id: UUID,
    deployment_id: str,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    return await _deployment_action(
        request,
        agent_id=agent_id,
        deployment_id=deployment_id,
        action="rollback",
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )


@router.get("/{agent_id}/evidence-packs")
async def list_evidence_packs(
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
    packs = await request.app.state.cp.deployments.list_evidence_packs(agent=agent)
    return {"items": [evidence_pack_payload(pack) for pack in packs]}
