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
from loop_control_plane.eval_suites import EvalCaseCreate
from loop_control_plane.migration_runs import (
    CutoverAdvance,
    CutoverRollback,
    MigrationImportCreate,
    MigrationRepairAccept,
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


async def _create_repair_eval_case(
    request: Request,
    *,
    workspace_id: UUID,
    run: Any,
    repair_id: str,
    payload: MigrationRepairAccept,
    caller_sub: str,
) -> dict[str, str]:
    resolved_item = next(
        (
            item
            for item in run.inventory
            if item.resolved_by_repair_id == repair_id
        ),
        None,
    )
    if resolved_item is None:
        raise WorkspaceError(f"accepted repair did not resolve an inventory item: {repair_id}")

    cp = request.app.state.cp
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name=f"Migration parity - {run.target_agent_name}",
        dataset_ref=f"agent:{run.target_agent_id}:migration:{run.id}:parity",
        metrics=["migration_parity", "regression_guard", "tool_safety"],
        actor_sub=caller_sub,
    )
    evidence_ref = payload.evidence_ref or resolved_item.evidence_ref
    case = await cp.eval_suites.add_case(
        workspace_id=workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=f"Migration repair regression: {resolved_item.label}",
            input={
                "migration_id": run.id,
                "source": run.source,
                "archive_name": run.archive_name,
                "archive_sha": run.archive_sha,
                "agent_id": str(run.target_agent_id),
                "branch_id": run.target_branch_id,
                "change_set_id": run.target_change_set_id,
                "repair_id": repair_id,
                "inventory_item_id": resolved_item.id,
                "inventory_kind": resolved_item.kind,
                "source_artifact": f"{run.source}.{resolved_item.kind}",
                "loop_target": resolved_item.loop_target,
                "patch_summary": payload.patch_summary,
                "evidence_ref": evidence_ref,
            },
            expected={
                "outcome": (
                    f"{resolved_item.label} remains mapped to "
                    f"{resolved_item.loop_target} without parity regression."
                ),
                "severity": "ok",
                "cutover_blocking": False,
            },
            scorers=[
                {
                    "kind": "migration_parity",
                    "config": {
                        "source": run.source,
                        "inventory_item_id": resolved_item.id,
                    },
                },
                {
                    "kind": "trace_regression",
                    "config": {
                        "migration_id": run.id,
                        "archive_sha": run.archive_sha,
                    },
                },
            ],
            source="migration_repair",
            source_ref=f"migration/{run.id}/repair/{repair_id}",
            attachments=[
                evidence_ref,
                run.target_branch_id,
                run.target_change_set_id,
            ],
        ),
        actor_sub=caller_sub,
    )
    return {
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "repair_id": repair_id,
        "source_ref": f"migration/{run.id}/repair/{repair_id}",
        "evidence_ref": evidence_ref,
    }


async def _create_initial_parity_eval_cases(
    request: Request,
    *,
    workspace_id: UUID,
    run: Any,
    caller_sub: str,
) -> list[dict[str, str]]:
    cp = request.app.state.cp
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name=f"Migration parity - {run.target_agent_name}",
        dataset_ref=f"agent:{run.target_agent_id}:migration:{run.id}:parity",
        metrics=["migration_parity", "regression_guard", "tool_safety"],
        actor_sub=caller_sub,
    )
    source_ref_base = f"migration/{run.id}/import"
    case_specs: list[EvalCaseCreate] = [
        EvalCaseCreate(
            name=f"Migration parity smoke: {run.archive_name}",
            input={
                "migration_id": run.id,
                "source": run.source,
                "archive_name": run.archive_name,
                "archive_sha": run.archive_sha,
                "agent_id": str(run.target_agent_id),
                "branch_id": run.target_branch_id,
                "change_set_id": run.target_change_set_id,
                "inventory_total": sum(item.count for item in run.inventory),
                "lineage_steps": [step.id for step in run.lineage_steps],
            },
            expected={
                "outcome": (
                    "Imported behavior is represented by Loop primitives with "
                    "source lineage, parity replay, and rollback evidence."
                ),
                "minimum_parity_score": 95,
                "cutover_blocking": run.readiness.blocking_count > 0,
            },
            scorers=[
                {
                    "kind": "migration_parity",
                    "config": {"source": run.source, "mode": "smoke"},
                },
                {
                    "kind": "trace_regression",
                    "config": {"migration_id": run.id},
                },
            ],
            source="migration_import",
            source_ref=f"{source_ref_base}/smoke",
            attachments=[
                run.archive_sha,
                run.target_branch_id,
                run.target_change_set_id,
            ],
        )
    ]
    if run.readiness.parity_total > 0:
        case_specs.append(
            EvalCaseCreate(
                name=f"Migration transcript replay: {run.archive_name}",
                input={
                    "migration_id": run.id,
                    "source": run.source,
                    "archive_name": run.archive_name,
                    "agent_id": str(run.target_agent_id),
                    "sample_count": min(run.readiness.parity_total, 20),
                    "parity_total": run.readiness.parity_total,
                    "parity_passing": run.readiness.parity_passing,
                },
                expected={
                    "outcome": (
                        "Historical source conversations produce equivalent "
                        "answers, tool calls, escalation, and safety outcomes."
                    ),
                    "minimum_pass_rate": 0.95,
                    "no_regressions": True,
                },
                scorers=[
                    {
                        "kind": "migration_transcript_replay",
                        "config": {
                            "source": run.source,
                            "archive_sha": run.archive_sha,
                        },
                    },
                    {
                        "kind": "llm_judge",
                        "config": {"rubric": "source parity and safe escalation"},
                    },
                ],
                source="migration_transcript",
                source_ref=f"{source_ref_base}/transcripts",
                attachments=[run.archive_sha, f"migration/{run.id}/parity"],
            )
        )
    for item in run.inventory:
        if item.severity == "ok":
            continue
        case_specs.append(
            EvalCaseCreate(
                name=f"Migration inventory guard: {item.label}",
                input={
                    "migration_id": run.id,
                    "source": run.source,
                    "archive_name": run.archive_name,
                    "agent_id": str(run.target_agent_id),
                    "inventory_item_id": item.id,
                    "inventory_kind": item.kind,
                    "count": item.count,
                    "loop_target": item.loop_target,
                    "confidence": item.confidence,
                    "severity": item.severity,
                    "evidence_ref": item.evidence_ref,
                },
                expected={
                    "outcome": (
                        f"{item.label} is mapped to {item.loop_target} or "
                        "explicitly blocked before cutover."
                    ),
                    "cutover_blocking": item.severity == "blocking",
                },
                scorers=[
                    {
                        "kind": "migration_inventory_mapping",
                        "config": {"inventory_item_id": item.id},
                    },
                    {
                        "kind": "regression_guard",
                        "config": {"source": run.source},
                    },
                ],
                source="migration_inventory",
                source_ref=f"{source_ref_base}/inventory/{item.id}",
                attachments=[item.evidence_ref, run.target_change_set_id],
            )
        )

    refs: list[dict[str, str]] = []
    for case_spec in case_specs:
        case = await cp.eval_suites.add_case(
            workspace_id=workspace_id,
            suite_id=suite.id,
            body=case_spec,
            actor_sub=caller_sub,
        )
        refs.append(
            {
                "suite_id": str(suite.id),
                "case_id": str(case.id),
                "repair_id": "",
                "source_ref": case_spec.source_ref,
                "evidence_ref": case_spec.attachments[0] if case_spec.attachments else "",
            }
        )
    return refs


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
        eval_refs = await _create_initial_parity_eval_cases(
            request,
            workspace_id=workspace_id,
            run=run,
            caller_sub=caller_sub,
        )
        for eval_ref in reversed(eval_refs):
            run = await cp.migration_runs.record_eval_case_ref(
                workspace_id=workspace_id,
                migration_id=run.id,
                eval_ref=eval_ref,
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
            "generated_eval_cases": len(run.eval_case_refs),
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


@router.post("/{workspace_id}/migrations/imports/{migration_id}/repairs/{repair_id}/accept")
async def accept_migration_repair(
    request: Request,
    workspace_id: UUID,
    migration_id: str,
    repair_id: str,
    body: MigrationRepairAccept,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorise(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        admin=True,
    )
    payload = body.model_copy(update={"repair_id": repair_id})
    try:
        run = await request.app.state.cp.migration_runs.accept_repair(
            workspace_id=workspace_id,
            migration_id=migration_id,
            body=payload,
            actor_sub=caller_sub,
        )
        eval_ref = await _create_repair_eval_case(
            request,
            workspace_id=workspace_id,
            run=run,
            repair_id=repair_id,
            payload=payload,
            caller_sub=caller_sub,
        )
        run = await request.app.state.cp.migration_runs.record_eval_case_ref(
            workspace_id=workspace_id,
            migration_id=migration_id,
            eval_ref=eval_ref,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="migration:repair_accept",
        resource_type="migration_run",
        resource_id=run.id,
        payload={
            "repair_id": repair_id,
            "status": run.status,
            "blocking_count": run.readiness.blocking_count,
            "evidence_ref": payload.evidence_ref,
            "eval_case": eval_ref,
        },
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
