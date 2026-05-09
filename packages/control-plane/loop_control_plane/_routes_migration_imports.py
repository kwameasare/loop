from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_agents import AgentCreate
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_commitments import CommitmentBody
from loop_control_plane.agent_workflow import BranchCreate, ChangeSetCreate
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.migration_runs import (
    CutoverAdvance,
    CutoverRollback,
    MigrationImportCreate,
    migration_run_payload,
    migration_run_summary,
    slugify_agent_name,
)
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/workspaces", tags=["MigrationImports"])


async def _authorise(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    admin: bool = False,
) -> None:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN if admin else None,
    )


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


async def _create_agent_with_available_slug(
    request: Request,
    *,
    workspace_id: UUID,
    body: MigrationImportCreate,
) -> Any:
    cp = request.app.state.cp
    base_slug = body.target_agent_slug or slugify_agent_name(body.target_agent_name)
    for attempt in range(0, 5):
        suffix = "" if attempt == 0 else f"-{attempt + 1}"
        slug = f"{base_slug[: 64 - len(suffix)]}{suffix}"
        try:
            return await cp.agents.create(
                workspace_id=workspace_id,
                body=AgentCreate(
                    name=body.target_agent_name,
                    slug=slug,
                    description=body.business_responsibility
                    or f"Migrated {body.source} agent from {body.archive_name}.",
                ),
            )
        except WorkspaceError:
            if attempt == 4:
                raise
    raise WorkspaceError(f"agent slug already taken: {base_slug}")


def _commitment_body(body: MigrationImportCreate, *, actor_sub: str) -> CommitmentBody:
    return CommitmentBody(
        business_responsibility=body.business_responsibility
        or f"Migrated {body.source} agent from {body.archive_name}.",
        target_users="Customers and operators served by the imported production agent.",
        owner_user_id=actor_sub,
        backup_owner_user_id="",
        worst_case_failure="Imported behavior diverges from the source platform during cutover.",
        channels=body.channels or ["web_chat"],
        systems_touched=[body.source, "loop-studio"],
        regions=["global"],
        languages=["en"],
        success_metric="Parity score is at least 95% before production cutover.",
        compliance_domain="migration",
        expected_volume=(
            f"{body.transcript_count} historical transcripts available"
            if body.transcript_count
            else "Historical volume unknown"
        ),
        launch_date="pending parity and approval",
        budget_target="Cost-per-turn does not exceed 150% of source baseline.",
        out_of_scope="Direct production overwrite before parity, approval, and rollback evidence.",
        escalation_policy="Rollback to source-platform routing if canary guardrails fail.",
    )


@router.get("/{workspace_id}/migrations/imports")
async def list_migration_imports(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    runs = await request.app.state.cp.migration_runs.list_for_workspace(workspace_id)
    return {"items": [migration_run_summary(run) for run in runs]}


@router.post("/{workspace_id}/migrations/imports", status_code=201)
async def create_migration_import(
    request: Request,
    workspace_id: UUID,
    body: MigrationImportCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    cp = request.app.state.cp
    try:
        agent = await _create_agent_with_available_slug(
            request,
            workspace_id=workspace_id,
            body=body,
        )
        commitment = await cp.agent_commitments.save_draft(
            agent=agent,
            body=_commitment_body(body, actor_sub=caller_sub),
            created_from=f"migration:{body.source}",
        )
        branch = await cp.agent_workflows.create_branch(
            agent=agent,
            body=BranchCreate(
                name=f"migration/{body.source}/{body.archive_name}",
                base_version_id="source-platform",
            ),
            actor_sub=caller_sub,
        )
        change_set = await cp.agent_workflows.create_change_set(
            agent=agent,
            body=ChangeSetCreate(
                branch_id=branch.id,
                name=f"Map {body.source} archive to Loop primitives",
                summary=(
                    "Imported artifacts become reviewable behavior, tool, "
                    "knowledge, channel, memory, and eval changes."
                ),
                source_type=f"migration:{body.source}",
                source_refs=[body.archive_name],
                changed_objects=[
                    {
                        "type": "migration_inventory",
                        "source": body.source,
                        "archive": body.archive_name,
                        "counts": body.inventory,
                        "transcript_count": body.transcript_count,
                    }
                ],
            ),
            actor_sub=caller_sub,
        )
        run = await cp.migration_runs.create(
            workspace_id=workspace_id,
            body=body,
            target_agent_id=agent.id,
            target_branch_id=branch.id,
            target_change_set_id=change_set.id,
            commitment_document_id=commitment.id,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="migration:import_create",
        resource_type="migration_run",
        resource_id=run.id,
        payload={
            "source": run.source,
            "archive_name": run.archive_name,
            "target_agent_id": str(run.target_agent_id),
            "target_branch_id": run.target_branch_id,
            "target_change_set_id": run.target_change_set_id,
        },
    )
    return migration_run_payload(run)


@router.get("/{workspace_id}/migrations/imports/{migration_id}")
async def get_migration_import(
    request: Request,
    workspace_id: UUID,
    migration_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(request, workspace_id=workspace_id, caller_sub=caller_sub)
    try:
        run = await request.app.state.cp.migration_runs.get(
            workspace_id=workspace_id,
            migration_id=migration_id,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return migration_run_payload(run)


@router.post("/{workspace_id}/migrations/imports/{migration_id}/cutover/advance")
async def advance_migration_cutover(
    request: Request,
    workspace_id: UUID,
    migration_id: str,
    body: CutoverAdvance,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    try:
        run = await request.app.state.cp.migration_runs.advance_cutover(
            workspace_id=workspace_id,
            migration_id=migration_id,
            body=body,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="migration:cutover_advance",
        resource_type="migration_run",
        resource_id=run.id,
        payload={"stage_id": body.stage_id, "status": run.status},
    )
    return migration_run_payload(run)


@router.post("/{workspace_id}/migrations/imports/{migration_id}/cutover/rollback")
async def rollback_migration_cutover(
    request: Request,
    workspace_id: UUID,
    migration_id: str,
    body: CutoverRollback,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    try:
        run = await request.app.state.cp.migration_runs.rollback(
            workspace_id=workspace_id,
            migration_id=migration_id,
            body=body,
            actor_sub=caller_sub,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="migration:cutover_rollback",
        resource_type="migration_run",
        resource_id=run.id,
        payload={"trigger_id": body.trigger_id, "status": run.status},
    )
    return migration_run_payload(run)


__all__ = ["router"]
