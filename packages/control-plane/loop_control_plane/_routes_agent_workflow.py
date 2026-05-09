from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_versions import AgentVersionCreate
from loop_control_plane.agent_workflow import (
    BranchCreate,
    ChangeSetCreate,
    ChangeSetTestResult,
    ReleaseCandidateApproval,
    ReleaseCandidateCreate,
    ReleaseCandidateGateUpdate,
    branch_payload,
    change_set_payload,
    release_candidate_payload,
    workflow_payload,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["AgentWorkflow"])


async def _agent(
    request: Request,
    agent_id: UUID,
    caller_sub: str,
    *,
    admin: bool = False,
) -> Any:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=agent.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN if admin else None,
    )
    return agent


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: object | None = None,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/workflow")
async def get_agent_workflow(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub)
    (
        branches,
        change_sets,
        release_candidates,
    ) = await request.app.state.cp.agent_workflows.list_for_agent(agent=agent)
    return workflow_payload(
        branches=branches,
        change_sets=change_sets,
        release_candidates=release_candidates,
    )


@router.post("/{agent_id}/branches", status_code=201)
async def create_branch(
    request: Request,
    agent_id: UUID,
    body: BranchCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    branch = await request.app.state.cp.agent_workflows.create_branch(
        agent=agent,
        body=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:branch_create",
        resource_type="agent_branch",
        resource_id=branch.id,
        payload={"agent_id": str(agent_id), "base_version_id": branch.base_version_id},
    )
    return branch_payload(branch)


@router.post("/{agent_id}/change-sets", status_code=201)
async def create_change_set(
    request: Request,
    agent_id: UUID,
    body: ChangeSetCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    try:
        change_set = await request.app.state.cp.agent_workflows.create_change_set(
            agent=agent,
            body=body,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:change_set_create",
        resource_type="agent_change_set",
        resource_id=change_set.id,
        payload={"agent_id": str(agent_id), "branch_id": change_set.branch_id},
    )
    return change_set_payload(change_set)


@router.post("/{agent_id}/change-sets/{change_set_id}/ready-for-tests")
async def mark_change_set_ready_for_tests(
    request: Request,
    agent_id: UUID,
    change_set_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    try:
        change_set = await request.app.state.cp.agent_workflows.mark_ready_for_tests(
            agent=agent,
            change_set_id=change_set_id,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:change_set_ready_for_tests",
        resource_type="agent_change_set",
        resource_id=change_set.id,
        payload={"agent_id": str(agent_id), "status": change_set.status},
    )
    return change_set_payload(change_set)


@router.post("/{agent_id}/change-sets/{change_set_id}/ready-for-review")
async def mark_change_set_ready_for_review(
    request: Request,
    agent_id: UUID,
    change_set_id: str,
    body: ChangeSetTestResult,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    try:
        change_set = await request.app.state.cp.agent_workflows.mark_ready_for_review(
            agent=agent,
            change_set_id=change_set_id,
            body=body,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:change_set_ready_for_review",
        resource_type="agent_change_set",
        resource_id=change_set.id,
        payload={
            "agent_id": str(agent_id),
            "eval_results_ref": change_set.eval_results_ref,
            "required_eval_suites": change_set.required_eval_suites,
        },
    )
    return change_set_payload(change_set)


@router.post(
    "/{agent_id}/change-sets/{change_set_id}/release-candidates",
    status_code=201,
)
async def create_release_candidate(
    request: Request,
    agent_id: UUID,
    change_set_id: str,
    body: ReleaseCandidateCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    branches, change_sets, _ = await request.app.state.cp.agent_workflows.list_for_agent(
        agent=agent
    )
    change_set = next((item for item in change_sets if item.id == change_set_id), None)
    if change_set is None:
        raise HTTPException(status_code=404, detail="unknown change set")
    if change_set.status != "ready_for_review":
        raise HTTPException(status_code=400, detail="change set must be ready_for_review")
    branch = next((item for item in branches if item.id == change_set.branch_id), None)
    try:
        version = await request.app.state.cp.agent_versions.create(
            workspace_id=agent.workspace_id,
            agent_id=agent_id,
            body=AgentVersionCreate(
                spec={
                    "branch_id": change_set.branch_id,
                    "change_set_id": change_set.id,
                    "changed_objects": change_set.changed_objects,
                    "eval_results_ref": change_set.eval_results_ref,
                    "required_eval_suites": body.required_eval_suites
                    or change_set.required_eval_suites,
                    "deploy_state": "inactive",
                    "eval_status": "passed",
                },
                notes=f"Release candidate for {change_set.name}",
            ),
            actor_sub=caller_sub,
        )
        release_candidate = await request.app.state.cp.agent_workflows.create_release_candidate(
            agent=agent,
            change_set_id=change_set_id,
            candidate_version_id=str(version.id),
            body=body,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:release_candidate_create",
        resource_type="agent_release_candidate",
        resource_id=release_candidate.id,
        payload={
            "agent_id": str(agent_id),
            "branch_id": branch.id if branch is not None else change_set.branch_id,
            "change_set_id": change_set_id,
            "candidate_version_id": str(version.id),
            "status": release_candidate.status,
        },
    )
    return release_candidate_payload(release_candidate)


@router.post("/{agent_id}/release-candidates/{release_candidate_id}/gate")
async def update_release_candidate_gate(
    request: Request,
    agent_id: UUID,
    release_candidate_id: str,
    body: ReleaseCandidateGateUpdate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    try:
        release_candidate = await request.app.state.cp.agent_workflows.update_gate(
            agent=agent,
            release_candidate_id=release_candidate_id,
            body=body,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:release_candidate_gate",
        resource_type="agent_release_candidate",
        resource_id=release_candidate.id,
        payload={"agent_id": str(agent_id), "gate_id": body.gate_id, "status": body.status},
    )
    return release_candidate_payload(release_candidate)


@router.post("/{agent_id}/release-candidates/{release_candidate_id}/approve")
async def approve_release_candidate(
    request: Request,
    agent_id: UUID,
    release_candidate_id: str,
    body: ReleaseCandidateApproval,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    try:
        release_candidate = await request.app.state.cp.agent_workflows.approve(
            agent=agent,
            release_candidate_id=release_candidate_id,
            body=body,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="agent_workflow:release_candidate_approve",
        resource_type="agent_release_candidate",
        resource_id=release_candidate.id,
        payload={
            "agent_id": str(agent_id),
            "approval_id": body.approval_id,
            "status": release_candidate.status,
        },
    )
    return release_candidate_payload(release_candidate)


__all__ = ["router"]
