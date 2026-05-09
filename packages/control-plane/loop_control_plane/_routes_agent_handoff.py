from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.agent_commitments import (
    CommitmentBody,
    commitment_payload,
    missing_required_fields,
)
from loop_control_plane.agent_handoff import (
    OwnershipTransferCreate,
    transfer_payload,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/agents", tags=["AgentHandoff"])


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


def _risk(
    *,
    risk_id: str,
    severity: str,
    title: str,
    detail: str,
    evidence_ref: str,
) -> dict[str, str]:
    return {
        "id": risk_id,
        "severity": severity,
        "title": title,
        "detail": detail,
        "evidence_ref": evidence_ref,
    }


def _section(
    *,
    section_id: str,
    title: str,
    summary: str,
    count: int,
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "summary": summary,
        "count": count,
        "evidence_refs": evidence_refs,
    }


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
        resource_type="agent_handoff",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


async def _handoff_model(request: Request, *, agent: Any) -> dict[str, Any]:
    cp = request.app.state.cp
    commitment = await cp.agent_commitments.current(agent=agent)
    commitments = await cp.agent_commitments.history(agent=agent)
    change_packages = await cp.change_packages.list_for_agent(agent=agent)
    deployments = await cp.deployments.list_for_agent(agent=agent)
    evidence_packs = await cp.deployments.list_evidence_packs(agent=agent)
    incidents = await cp.incidents.list_for_workspace(
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
    )
    versions = await cp.agent_versions.list_for_agent(
        workspace_id=agent.workspace_id,
        agent_id=agent.id,
    )
    transfers = await cp.agent_handoffs.list_for_agent(agent=agent)
    comment_resolutions = list(
        getattr(cp, "ux_wireup", {}).get("comment_resolutions", {}).get(str(agent.id), [])
    )
    risks: list[dict[str, str]] = []
    missing = missing_required_fields(commitment.body)
    if missing:
        risks.append(
            _risk(
                risk_id="commitment_missing_fields",
                severity="blocking",
                title="Commitment is incomplete",
                detail="Missing required fields: " + ", ".join(missing),
                evidence_ref=f"commitment/{commitment.id}",
            )
        )
    pending_packages = [
        package
        for package in change_packages
        if package.status in {"generated", "submitted", "approved"}
        and package.approval_status not in {"approved", "deployable"}
    ]
    if pending_packages:
        risks.append(
            _risk(
                risk_id="pending_change_package_approval",
                severity="advisory",
                title="Change Package approval is still open",
                detail=f"{len(pending_packages)} Change Package(s) require review.",
                evidence_ref=f"change-package/{pending_packages[-1].id}",
            )
        )
    open_incidents = [
        incident for incident in incidents if incident.status not in {"resolved", "archived"}
    ]
    if open_incidents:
        risks.append(
            _risk(
                risk_id="open_incidents",
                severity="blocking",
                title="Open incidents require handoff context",
                detail=f"{len(open_incidents)} incident(s) remain active.",
                evidence_ref=f"incident/{open_incidents[0].id}",
            )
        )
    live_deployments = [
        deployment
        for deployment in deployments
        if deployment.status in {"pending", "canary", "paused"}
    ]
    if live_deployments:
        risks.append(
            _risk(
                risk_id="active_rollout",
                severity="advisory",
                title="Rollout is not settled",
                detail=f"{len(live_deployments)} deployment(s) are still active.",
                evidence_ref=f"deployment/{live_deployments[0].id}",
            )
        )
    sections = [
        _section(
            section_id="commitments",
            title="Commitment changes",
            summary=f"{len(commitments)} Commitment Document version(s).",
            count=len(commitments),
            evidence_refs=[f"commitment/{item.id}" for item in commitments[-5:]],
        ),
        _section(
            section_id="versions",
            title="Major behavior versions",
            summary=f"{len(versions)} immutable agent version(s).",
            count=len(versions),
            evidence_refs=[f"version/{item.id}" for item in versions[-5:]],
        ),
        _section(
            section_id="change-packages",
            title="Change Packages and approvals",
            summary=f"{len(change_packages)} preflight evidence package(s).",
            count=len(change_packages),
            evidence_refs=[f"change-package/{item.id}" for item in change_packages[-5:]],
        ),
        _section(
            section_id="deployments",
            title="Deployments and rollbacks",
            summary=f"{len(deployments)} rollout event(s), {len(evidence_packs)} evidence pack(s).",
            count=len(deployments),
            evidence_refs=[f"deployment/{item.id}" for item in deployments[-5:]],
        ),
        _section(
            section_id="incidents",
            title="Incidents and candidate evals",
            summary=f"{len(incidents)} incident record(s).",
            count=len(incidents),
            evidence_refs=[f"incident/{item.id}" for item in incidents[:5]],
        ),
        _section(
            section_id="important-comments",
            title="Important reviewer comments",
            summary=(
                f"{len(comment_resolutions)} resolved reviewer comment(s), "
                "including comments converted to eval cases."
            ),
            count=len(comment_resolutions),
            evidence_refs=[
                (
                    f"comment/{item.get('comment_id')}"
                    if not item.get("case_id")
                    else f"comment/{item.get('comment_id')} -> eval/{item.get('case_id')}"
                )
                for item in comment_resolutions[-5:]
            ],
        ),
    ]
    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "slug": agent.slug,
            "description": agent.description,
        },
        "owner_user_id": commitment.body.owner_user_id,
        "backup_owner_user_id": commitment.body.backup_owner_user_id,
        "commitment": commitment_payload(commitment),
        "open_risks": risks,
        "walkthrough_sections": sections,
        "transfers": [transfer_payload(record) for record in transfers],
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/{agent_id}/handoff")
async def get_agent_handoff(
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
    return await _handoff_model(request, agent=agent)


@router.post("/{agent_id}/handoff/transfer")
async def transfer_agent_owner(
    request: Request,
    agent_id: UUID,
    body: OwnershipTransferCreate,
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
    cp = request.app.state.cp
    commitment = await cp.agent_commitments.current(agent=agent)
    try:
        transfer = await cp.agent_handoffs.create_transfer(
            agent=agent,
            previous_owner_user_id=commitment.body.owner_user_id,
            body=body,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated_body = CommitmentBody(
        **{
            **commitment.body.model_dump(mode="python"),
            "owner_user_id": body.new_owner_user_id,
            "backup_owner_user_id": body.backup_owner_user_id,
        }
    )
    await cp.agent_commitments.save_draft(
        agent=agent,
        body=updated_body,
        created_from="handoff:ownership_transfer",
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_handoff:ownership_transfer",
        resource_id=transfer.id,
        payload={
            "agent_id": str(agent_id),
            "previous_owner_user_id": transfer.previous_owner_user_id,
            "new_owner_user_id": transfer.new_owner_user_id,
            "backup_owner_user_id": transfer.backup_owner_user_id,
            "acknowledged_risk_ids": transfer.acknowledged_risk_ids,
            "history_walkthrough_id": transfer.history_walkthrough_id,
        },
    )
    return await _handoff_model(request, agent=agent)


__all__ = ["router"]
