from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.compliance_review import (
    ComplianceEvidenceExportCreate,
    ComplianceProbeSuiteAttachCreate,
    build_compliance_review_payload,
    build_evidence_export_payload,
    get_probe_library,
    probe_case_body,
)
from loop_control_plane.eval_suites import serialise_case, serialise_suite

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


def _recommended_probe_agent_ids(review: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in review["approval_queue"]:
        if item["risk_class"] in {"high", "critical"}:
            ids.add(str(item["agent_id"]))
    for item in review["tool_grants"]:
        if (
            item["pii_access"]
            or item["money_movement"]
            or item["live_status"]
            in {
                "blocked",
                "review_required",
            }
        ):
            ids.add(str(item["agent_id"]))
    for item in review["memory_policies"]:
        if item["approval_status"] in {"blocked", "review_required"}:
            ids.add(str(item["agent_id"]))
    for item in review["channel_readiness"]:
        if item["blocking_checks"]:
            ids.add(str(item["agent_id"]))
    return ids


@router.post(
    "/{workspace_id}/compliance-review/probe-libraries/{library_id}/attach",
    status_code=201,
)
async def attach_compliance_probe_library(
    request: Request,
    workspace_id: UUID,
    library_id: str,
    body: ComplianceProbeSuiteAttachCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    library = get_probe_library(library_id)
    if library is None:
        raise HTTPException(status_code=404, detail="unknown probe library")

    cp = request.app.state.cp
    agents = await cp.agents.list_for_workspace(workspace_id)
    if body.agent_id is not None:
        agents = [agent for agent in agents if agent.id == body.agent_id]
        if not agents:
            raise HTTPException(status_code=404, detail="unknown agent")
    else:
        review = await _review_payload(request, workspace_id=workspace_id)
        recommended_ids = _recommended_probe_agent_ids(review)
        agents = [agent for agent in agents if str(agent.id) in recommended_ids]

    attached_agents: list[dict[str, Any]] = []
    for agent in agents:
        suite = await cp.eval_suites.get_or_create_suite(
            workspace_id=workspace_id,
            name=f"{library['name']}: {agent.slug}"[:128],
            dataset_ref=f"compliance-probes/{library_id}/{agent.id}",
            metrics=list(library["metrics"]),
            actor_sub=caller_sub,
        )
        existing_cases = await cp.eval_suites.list_cases(
            workspace_id=workspace_id,
            suite_id=suite.id,
        )
        existing_source_refs = {case.source_ref for case in existing_cases}
        added_cases = []
        skipped_existing = 0
        for template in library["cases"]:
            case_body = probe_case_body(
                library_id=library_id,
                template=template,
                agent=agent,
            )
            if case_body.source_ref in existing_source_refs:
                skipped_existing += 1
                continue
            case = await cp.eval_suites.add_case(
                workspace_id=workspace_id,
                suite_id=suite.id,
                body=case_body,
                actor_sub=caller_sub,
            )
            added_cases.append(serialise_case(case))

        attached_agents.append(
            {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "suite": serialise_suite(suite),
                "cases_added": added_cases,
                "cases_existing": skipped_existing,
                "evidence_ref": f"eval-suite/{suite.id}",
            }
        )

    result = {
        "library_id": library_id,
        "library_name": library["name"],
        "status": "attached" if attached_agents else "no_recommended_agents",
        "attached_agents": attached_agents,
        "suite_count": len(attached_agents),
        "case_count": sum(len(item["cases_added"]) for item in attached_agents),
    }
    audit_event = record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="compliance:probe_suite_attach",
        resource_type="compliance_probe_library",
        resource_id=library_id,
        store=cp.audit_events,
        request_id=request_id(request),
        payload={
            "library_id": library_id,
            "agent_ids": [item["agent_id"] for item in attached_agents],
            "suite_count": result["suite_count"],
            "case_count": result["case_count"],
        },
    )
    result["audit_ref"] = f"audit/{audit_event.id}"
    return result


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
