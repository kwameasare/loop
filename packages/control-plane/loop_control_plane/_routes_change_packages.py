from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.change_packages import (
    ChangePackageApprovalAction,
    ChangePackageApprovalExpiry,
    ChangePackageGenerate,
    change_package_payload,
    infer_change_risk,
    infer_change_types,
)
from loop_control_plane.preapproved_classes import RiskCeiling, preapproved_class_payload
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["ChangePackages"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    cp = request.app.state.cp
    if workspace_id is None:
        agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
        if agent is None:
            raise HTTPException(status_code=404, detail="unknown agent")
        workspace_id = agent.workspace_id
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return await cp.agents.get(
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


def _build_approval_notifications(
    *,
    agent_id: UUID,
    package: Any,
) -> list[dict[str, Any]]:
    notifications: list[dict[str, Any]] = []
    for approval in package.required_approvals:
        if not approval.get("required") or approval.get("satisfied"):
            continue
        approval_id = str(approval.get("id", "approval"))
        role = str(approval.get("role", "Approver"))
        notifications.append(
            {
                "id": f"notify_{package.id}_{approval_id}",
                "change_package_id": package.id,
                "approval_id": approval_id,
                "recipient_role": role,
                "summary": (
                    f"{role} approval requested for {package.summary or package.id}."
                ),
                "deep_link": (
                    f"/agents/{agent_id}/deploys?change_package_id={package.id}"
                    f"&approval_id={approval_id}"
                ),
                "content_hash": package.content_hash,
                "state": "queued",
            }
        )
    return notifications


async def _release_candidate_for_preflight(
    request: Request,
    *,
    agent: Any,
    release_candidate_id: str,
) -> Any | None:
    if release_candidate_id in {"", "rc-current"}:
        return None
    _, _, release_candidates = await request.app.state.cp.agent_workflows.list_for_agent(
        agent=agent
    )
    release_candidate = next(
        (item for item in release_candidates if item.id == release_candidate_id),
        None,
    )
    if release_candidate is None:
        raise WorkspaceError(f"unknown release candidate: {release_candidate_id}")
    if release_candidate.status not in {"approved", "deployable"}:
        raise WorkspaceError(
            f"release candidate {release_candidate_id} must be approved or deployable before preflight"
        )
    return release_candidate


@router.get("/{agent_id}/change-packages")
async def list_change_packages(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )
    items = await request.app.state.cp.change_packages.list_for_agent(agent=agent)
    return {"items": [change_package_payload(item) for item in items]}


@router.get("/{agent_id}/change-packages/current")
async def get_current_change_package(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )
    current = await request.app.state.cp.change_packages.current(agent=agent)
    return {"item": change_package_payload(current) if current is not None else None}


@router.post("/{agent_id}/change-packages/preflight", status_code=201)
async def generate_change_package(
    request: Request,
    agent_id: UUID,
    body: ChangePackageGenerate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    commitment = await request.app.state.cp.agent_commitments.current(agent=agent)
    release_candidate = await _release_candidate_for_preflight(
        request,
        agent=agent,
        release_candidate_id=body.release_candidate_id,
    )
    if release_candidate is not None:
        body = body.model_copy(
            update={
                "branch_id": release_candidate.branch_id,
                "change_set_id": release_candidate.change_set_id,
                "to_version_id": release_candidate.candidate_version_id
                if body.to_version_id == "draft"
                else body.to_version_id,
            }
        )
    change_types = infer_change_types(body)
    risk = infer_change_risk(body)
    preapproved = await request.app.state.cp.preapproved_classes.applicable(
        agent=agent,
        change_types=change_types,
        risk=cast(RiskCeiling, risk),
        actor_sub=caller_sub,
    )
    package = await request.app.state.cp.change_packages.generate(
        agent=agent,
        commitment=commitment,
        body=body,
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
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="change_package:generate",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "content_hash": package.content_hash,
            "commitment_document_id": package.commitment_document_id,
            "status": package.status,
            "change_types": change_types,
            "risk": risk,
            "release_candidate_id": body.release_candidate_id,
            "release_candidate_status": release_candidate.status
            if release_candidate is not None
            else None,
            "pre_approved_classes": [record.id for record in preapproved],
        },
    )
    return change_package_payload(package)


@router.post("/{agent_id}/change-packages/{package_id}/approvals/expire")
async def expire_change_package_approvals(
    request: Request,
    agent_id: UUID,
    package_id: str,
    body: ChangePackageApprovalExpiry,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    package = await request.app.state.cp.change_packages.expire_approvals(
        agent=agent,
        package_id=package_id,
        body=body,
    )
    expired_ids = [
        approval.get("id")
        for approval in package.required_approvals
        if approval.get("state") == "expired"
    ]
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="change_package:approval_expire",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "expired_approval_ids": expired_ids,
            "reason": body.reason,
            "content_hash": package.content_hash,
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
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    package = await request.app.state.cp.change_packages.submit(
        agent=agent,
        package_id=package_id,
    )
    notifications = _build_approval_notifications(
        agent_id=agent_id,
        package=package,
    )
    request.app.state.cp.ux_wireup.setdefault(
        "change_package_approval_notifications", {}
    )[package.id] = notifications
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="change_package:submit",
        resource_id=package.id,
        payload={
            "agent_id": str(agent_id),
            "content_hash": package.content_hash,
            "status": package.status,
            "approval_notifications": notifications,
        },
    )
    return {
        **change_package_payload(package),
        "approval_notifications": notifications,
    }


@router.post("/{agent_id}/change-packages/{package_id}/approvals")
async def record_change_package_approval(
    request: Request,
    agent_id: UUID,
    package_id: str,
    body: ChangePackageApprovalAction,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    package = await request.app.state.cp.change_packages.record_approval(
        agent=agent,
        package_id=package_id,
        action=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
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
