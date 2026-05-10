from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_agents import AgentCreate, agent_payload
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_commitments import missing_required_fields
from loop_control_plane.agent_intake import (
    AgentIntakeCreate,
    AgentIntakeRecord,
    agent_intake_payload,
    apply_enterprise_template,
    build_intake_analysis,
    candidate_channel_specs,
    candidate_knowledge_sources,
    candidate_tool_specs,
    template_payloads,
)
from loop_control_plane.agent_versions import AgentVersionCreate
from loop_control_plane.agent_workflow import BranchCreate, branch_payload
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.channel_bindings import SUPPORTED_CHANNELS, ChannelBindingUpsert
from loop_control_plane.eval_suites import EvalCaseCreate
from loop_control_plane.kb_documents import KbDocumentCreate
from loop_control_plane.memory_policies import MemoryPolicyUpsert
from loop_control_plane.tool_contracts import ToolContractUpsert
from loop_control_plane.workspaces import WorkspaceError

router = APIRouter(prefix="/v1/workspaces", tags=["AgentIntake"])

_CLARIFICATION_BLOCKING_FIELDS = {
    "business_responsibility",
    "target_users",
    "owner_user_id",
    "worst_case_failure",
}


_CHANNEL_ALIASES = {
    "web": "web_chat",
    "webchat": "web_chat",
    "web_chat": "web_chat",
    "chat": "web_chat",
    "whatsapp": "whatsapp",
    "wa": "whatsapp",
    "telegram": "telegram",
    "slack": "slack",
    "teams": "teams",
    "msteams": "teams",
    "sms": "sms",
    "email": "email",
    "voice": "voice",
    "phone": "voice",
    "webhook": "webhook_api",
    "api": "webhook_api",
    "webhook_api": "webhook_api",
}


class AgentIntakeManualContinue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(default="", max_length=500)


def _channel_type(value: str) -> str | None:
    normalised = "".join(ch for ch in value.lower() if ch.isalnum() or ch == "_")
    channel = _CHANNEL_ALIASES.get(normalised)
    return channel if channel in SUPPORTED_CHANNELS else None


def _initial_behavior_spec(
    *,
    body: AgentIntakeCreate,
    commitment_id: str,
    channel_refs: list[dict[str, str]],
    tool_refs: list[dict[str, str]],
    knowledge_refs: list[dict[str, str]],
    memory_policy_id: str,
    eval_suite_id: str,
) -> dict[str, Any]:
    contract = body.contract
    channel_types = [item["channel_type"] for item in channel_refs]
    tool_ids = [item["tool_id"] for item in tool_refs]
    return {
        "created_from": f"agent_intake:{body.creation_path}",
        "commitment_document_id": commitment_id,
        "system_prompt": (
            f"You are responsible for: {contract.business_responsibility}. "
            f"Serve: {contract.target_users}. "
            f"Never do this failure mode: {contract.worst_case_failure}. "
            f"Escalation policy: {contract.escalation_policy or 'Escalate uncertainty to the owner.'}"
        ),
        "behavior": {
            "goals": [
                contract.business_responsibility,
                contract.success_metric or "Meet the accepted Commitment Document.",
            ],
            "constraints": [
                contract.out_of_scope or "Stay within the accepted Commitment Document.",
                contract.worst_case_failure,
            ],
            "escalation_policy": contract.escalation_policy,
            "owner_user_id": contract.owner_user_id,
            "backup_owner_user_id": contract.backup_owner_user_id,
            "compliance_domain": contract.compliance_domain,
        },
        "channels": channel_types,
        "tool_contracts": tool_ids,
        "knowledge_documents": [item["id"] for item in knowledge_refs],
        "memory_policy_id": memory_policy_id,
        "eval_suite_id": eval_suite_id,
        "artifact_refs": [artifact.source_ref or artifact.name for artifact in body.artifacts],
        "risk_notes": [
            {
                "kind": "worst_case_failure",
                "message": contract.worst_case_failure,
            }
        ],
    }


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


def _retry_inputs(request: Request) -> dict[str, dict[str, Any]]:
    return request.app.state.cp.ux_wireup.setdefault("agent_intake_retry_inputs", {})


def _store_retry_input(request: Request, *, intake_id: str, body: AgentIntakeCreate) -> None:
    _retry_inputs(request)[intake_id] = body.model_dump(mode="json")


def _load_retry_input(request: Request, *, intake_id: str) -> AgentIntakeCreate:
    raw = _retry_inputs(request).get(intake_id)
    if raw is None:
        raise WorkspaceError(
            f"retry payload unavailable for failed intake: {intake_id}"
        )
    return AgentIntakeCreate.model_validate(raw)


def _failed_generation_intake(
    *,
    body: AgentIntakeCreate,
    agent: Any,
    created_by: str,
    created_object_refs: dict[str, Any],
    stage: str,
    exc: Exception,
) -> AgentIntakeRecord:
    base = build_intake_analysis(
        body=body,
        agent=agent,
        created_by=created_by,
        created_object_refs=created_object_refs,
    )
    jobs = [
        {
            **job,
            "state": "failed"
            if job["name"] == "draft_agent_plan"
            else job["state"],
            "error": str(exc) if job["name"] == "draft_agent_plan" else "",
        }
        for job in base.jobs
    ]
    ready = [
        item
        for item in base.readiness.get("ready", [])
        if item
        not in {"Initial behavior generated", "Draft branch main/draft created"}
        and "sandbox channel binding" not in item
        and "mock tool contract" not in item
        and "Conversation memory policy drafted" not in item
    ]
    needs_attention = [
        *base.readiness.get("needs_attention", []),
        (
            "Draft generation failed after the agent and Commitment Document "
            "were created. Retry generation or continue with manual setup."
        ),
    ]
    refs = {
        **created_object_refs,
        "draft_generation_failed": True,
        "failure_stage": stage,
        "failure_message": str(exc),
        "retry_available": True,
        "manual_continue_available": True,
    }
    return base.model_copy(
        update={
            "state": "failed",
            "jobs": jobs,
            "readiness": {
                **base.readiness,
                "score": min(int(base.readiness.get("score", 0)), 40),
                "ready": ready,
                "needs_attention": needs_attention,
            },
            "created_object_refs": refs,
        }
    )


def _manual_continue_intake(
    *,
    record: AgentIntakeRecord,
    notes: str,
    caller_sub: str,
) -> AgentIntakeRecord:
    jobs = [
        {
            **job,
            "state": "skipped"
            if job["name"] == "draft_agent_plan"
            else job["state"],
            "error": "",
        }
        for job in record.jobs
    ]
    refs = {
        **record.created_object_refs,
        "manual_continue": True,
        "manual_continue_by": caller_sub,
        "manual_continue_notes": notes,
    }
    return record.model_copy(
        update={
            "state": "draft_ready",
            "jobs": jobs,
            "readiness": {
                **record.readiness,
                "score": max(int(record.readiness.get("score", 0)), 35),
                "ready": [
                    *record.readiness.get("ready", []),
                    "Manual Workbench setup selected",
                ],
                "needs_attention": [
                    "Create behavior, channel bindings, tool contracts, memory policy, and starter evals manually.",
                    *record.readiness.get("needs_attention", []),
                ],
                "landing": f"/agents/{record.agent_id}",
            },
            "created_object_refs": refs,
        }
    )


async def _create_draft_objects(
    *,
    request: Request,
    workspace_id: UUID,
    body: AgentIntakeCreate,
    agent: Any,
    commitment_id: str,
    caller_sub: str,
) -> dict[str, Any]:
    cp = request.app.state.cp
    channel_refs: list[dict[str, str]] = []
    for channel in candidate_channel_specs(body):
        requested = str(channel["channel"])
        channel_type = _channel_type(requested)
        if channel_type is None:
            continue
        binding = await cp.channel_bindings.upsert(
            agent=agent,
            body=ChannelBindingUpsert(
                channel_type=channel_type,  # type: ignore[arg-type]
                display_name=requested.strip() or channel_type,
                status="draft",
                identity_config={
                    "created_from": "agent_intake",
                    "source": channel.get("source", "contract:channels"),
                    "source_artifact": channel.get("source_artifact", ""),
                },
            ),
        )
        channel_refs.append({"id": binding.id, "channel_type": binding.channel_type})

    tool_refs: list[dict[str, str]] = []
    for tool in candidate_tool_specs(body):
        tool_id = str(tool["tool_id"])
        contract = await cp.tool_contracts.upsert(
            agent=agent,
            tool_id=tool_id,
            body=ToolContractUpsert(
                name=str(tool["name"]),
                description=(
                    f"{tool['description']} Source: "
                    f"{tool.get('source_artifact') or tool.get('source')}."
                ),
                side_effect_level="read",
                sandbox_status="mock",
                owner_user_id=body.contract.owner_user_id,
                failure_behavior=(
                    "Return unavailable in sandbox and preserve a trace span. "
                    f"Import mode: {tool.get('import_mode', 'manual_system')}."
                ),
            ),
        )
        tool_refs.append({"id": contract.id, "tool_id": contract.tool_id})

    knowledge_refs: list[dict[str, str]] = []
    for source in candidate_knowledge_sources(body):
        if source["status"] != "ready_for_ingestion":
            continue
        source_ref = str(source["source_ref"])
        if source_ref.startswith(("http://", "https://")):
            document = await cp.kb_documents.create(
                workspace_id=workspace_id,
                body=KbDocumentCreate(
                    source_url=source_ref,
                    title=str(source["name"]),
                ),
            )
        else:
            document = await cp.kb_documents.create_upload(
                workspace_id=workspace_id,
                filename=str(source["name"]),
                content_type=str(source["content_type"]),
                byte_size=int(source["byte_size"]),
            )
        knowledge_refs.append(
            {
                "id": str(document.id),
                "title": document.title,
                "source_ref": source_ref,
                "artifact": str(source["name"]),
            }
        )

    memory_policy = await cp.memory_policies.upsert(
        agent=agent,
        body=MemoryPolicyUpsert(
            scope="conversation",
            allowed_memory_types=["handoff_notes", "conversation_state"],
            retention="Retain for 30 days unless the workspace policy is shorter.",
            consent_requirement="No durable user memory without explicit consent.",
            pii_policy="Redact PII before writing memory drafts.",
            delete_behavior="Delete conversation memory when the conversation or user request is deleted.",
            privacy_implications=[
                "Short-lived state may include support context and must stay trace-backed."
            ],
            source_trace_required=True,
        ),
    )

    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name=f"{body.agent_name} starter evals",
        dataset_ref=f"agent:{agent.id}:starter",
        metrics=["behavior_match", "groundedness", "escalation_match"],
        actor_sub=caller_sub,
    )
    eval_refs: list[dict[str, str]] = []
    for case in build_intake_analysis(
        body=body,
        agent=agent,
        created_by=caller_sub,
        created_object_refs={},
    ).candidate_eval_cases:
        created_case = await cp.eval_suites.add_case(
            workspace_id=workspace_id,
            suite_id=suite.id,
            body=EvalCaseCreate(
                name=case["name"],
                input=case["input"],
                expected=case["expected"],
                scorers=[
                    {"kind": "llm_judge", "config": {"rubric": "agent contract adherence"}},
                    {"kind": "groundedness", "config": {"source": "intake"}},
                ],
                source=case["source"],
                source_ref=f"agent:{agent.id}:intake",
            ),
            actor_sub=caller_sub,
        )
        eval_refs.append({"id": str(created_case.id), "suite_id": str(suite.id)})

    initial_version = await cp.agent_versions.create(
        workspace_id=workspace_id,
        agent_id=agent.id,
        body=AgentVersionCreate(
            spec=_initial_behavior_spec(
                body=body,
                commitment_id=commitment_id,
                channel_refs=channel_refs,
                tool_refs=tool_refs,
                knowledge_refs=knowledge_refs,
                memory_policy_id=memory_policy.id,
                eval_suite_id=str(suite.id),
            ),
            notes="Initial governed draft from agent intake.",
        ),
        actor_sub=caller_sub,
    )
    branch = await cp.agent_workflows.create_branch(
        agent=agent,
        body=BranchCreate(name="main/draft", base_version_id=f"v{initial_version.version}"),
        actor_sub=caller_sub,
    )

    refs: dict[str, Any] = {
        "agent_id": str(agent.id),
        "commitment_id": commitment_id,
        "version_id": str(initial_version.id),
        "version": f"v{initial_version.version}",
        "branch_id": branch.id,
        "branch": branch_payload(branch),
        "channel_bindings": channel_refs,
        "tool_contracts": tool_refs,
        "knowledge_documents": knowledge_refs,
        "memory_policy_id": memory_policy.id,
        "eval_suite_id": str(suite.id),
        "eval_cases": eval_refs,
    }
    if body.template_id:
        refs["template_id"] = body.template_id
    return refs


@router.post("/{workspace_id}/agent-intakes", status_code=201)
async def create_agent_intake(
    request: Request,
    workspace_id: UUID,
    body: AgentIntakeCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        body = apply_enterprise_template(body, actor_sub=caller_sub)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    agent = await cp.agents.create(
        workspace_id=workspace_id,
        body=AgentCreate(
            name=body.agent_name,
            slug=body.slug,
            description=body.contract.business_responsibility,
        ),
    )
    commitment = await cp.agent_commitments.ensure_current(
        agent=agent,
        body=body.contract,
        created_from=f"agent_intake:{body.creation_path}",
    )
    contract_gaps = [
        field
        for field in missing_required_fields(body.contract)
        if field in _CLARIFICATION_BLOCKING_FIELDS
    ]
    if contract_gaps:
        refs = {
            "agent_id": str(agent.id),
            "commitment_id": commitment.id,
            "blocked_before_generation": True,
            "missing_required_fields": contract_gaps,
        }
        intake = await cp.agent_intakes.add(
            build_intake_analysis(
                body=body,
                agent=agent,
                created_by=caller_sub,
                created_object_refs=refs,
            )
        )
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="agent_intake:create",
            resource_type="agent_intake",
            resource_id=intake.id,
            payload={
                "agent_id": str(agent.id),
                "creation_path": body.creation_path,
                "template_id": body.template_id,
                "state": intake.state,
                "readiness_score": intake.readiness["score"],
                "artifacts": len(body.artifacts),
            },
        )
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="agent_intake:clarification_requested",
            resource_type="agent_intake",
            resource_id=intake.id,
            payload={
                "agent_id": str(agent.id),
                "missing_required_fields": contract_gaps,
                "questions": [
                    row.get("question", "")
                    for row in intake.missing_information
                    if row.get("severity") == "high"
                ],
            },
        )
        return {
            **agent_intake_payload(intake),
            "agent": {
                **agent_payload(agent),
                "object_state": "draft",
                "state_reason": "Commitment Document needs clarification before draft generation.",
                "state_evidence_ref": f"commitment/{commitment.id}",
            },
            "commitment": commitment.model_dump(mode="json"),
        }

    try:
        refs = await _create_draft_objects(
            request=request,
            workspace_id=workspace_id,
            body=body,
            agent=agent,
            commitment_id=commitment.id,
            caller_sub=caller_sub,
        )
    except Exception as exc:
        refs = {
            "agent_id": str(agent.id),
            "commitment_id": commitment.id,
        }
        if body.template_id:
            refs["template_id"] = body.template_id
        intake = await cp.agent_intakes.add(
            _failed_generation_intake(
                body=body,
                agent=agent,
                created_by=caller_sub,
                created_object_refs=refs,
                stage="draft_agent_plan",
                exc=exc,
            )
        )
        _store_retry_input(request, intake_id=intake.id, body=body)
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="agent_intake:create",
            resource_type="agent_intake",
            resource_id=intake.id,
            payload={
                "agent_id": str(agent.id),
                "creation_path": body.creation_path,
                "template_id": body.template_id,
                "state": intake.state,
                "readiness_score": intake.readiness["score"],
                "artifacts": len(body.artifacts),
            },
        )
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="agent_intake:generation_failed",
            resource_type="agent_intake",
            resource_id=intake.id,
            payload={
                "agent_id": str(agent.id),
                "failure_stage": "draft_agent_plan",
                "failure_message": str(exc),
                "retry_available": True,
                "manual_continue_available": True,
            },
        )
        return {
            **agent_intake_payload(intake),
            "agent": {
                **agent_payload(agent),
                "object_state": "draft",
                "state_reason": "Draft generation failed; retry or continue manually.",
                "state_evidence_ref": f"agent_intake/{intake.id}",
            },
            "commitment": commitment.model_dump(mode="json"),
        }
    intake = await cp.agent_intakes.add(
        build_intake_analysis(
            body=body,
            agent=agent,
            created_by=caller_sub,
            created_object_refs=refs,
        )
    )

    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_intake:create",
        resource_type="agent_intake",
        resource_id=intake.id,
        payload={
            "agent_id": str(agent.id),
            "creation_path": body.creation_path,
            "template_id": body.template_id,
            "state": intake.state,
            "readiness_score": intake.readiness["score"],
            "artifacts": len(body.artifacts),
        },
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_intake:draft_objects_create",
        resource_type="agent",
        resource_id=str(agent.id),
        payload=refs,
    )
    return {
        **agent_intake_payload(intake),
        "agent": {
            **agent_payload(agent),
            "object_state": "draft",
            "state_reason": "Commitment Document is still draft.",
            "state_evidence_ref": f"commitment/{commitment.id}",
        },
        "commitment": commitment.model_dump(mode="json"),
    }


@router.get("/{workspace_id}/agent-intakes")
async def list_agent_intakes(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    rows = await cp.agent_intakes.list_for_workspace(workspace_id)
    return {"items": [agent_intake_payload(row) for row in rows]}


@router.get("/{workspace_id}/agent-intake-templates")
async def list_agent_intake_templates(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return {"items": template_payloads()}


@router.post("/{workspace_id}/agent-intakes/{intake_id}/retry")
async def retry_agent_intake_generation(
    request: Request,
    workspace_id: UUID,
    intake_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        record = await cp.agent_intakes.get(workspace_id=workspace_id, intake_id=intake_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown intake: {intake_id}") from exc
    if record.state != "failed":
        raise WorkspaceError(f"intake {intake_id} is not in failed state")
    body = _load_retry_input(request, intake_id=intake_id)
    agent = await cp.agents.get(workspace_id=workspace_id, agent_id=record.agent_id)
    commitment = await cp.agent_commitments.current(agent=agent)
    try:
        refs = await _create_draft_objects(
            request=request,
            workspace_id=workspace_id,
            body=body,
            agent=agent,
            commitment_id=commitment.id,
            caller_sub=caller_sub,
        )
    except Exception as exc:
        retry_failed = _failed_generation_intake(
            body=body,
            agent=agent,
            created_by=record.created_by,
            created_object_refs={
                **record.created_object_refs,
                "agent_id": str(agent.id),
                "commitment_id": commitment.id,
            },
            stage="draft_agent_plan_retry",
            exc=exc,
        ).model_copy(update={"id": record.id, "created_at": record.created_at})
        await cp.agent_intakes.replace(retry_failed)
        _store_retry_input(request, intake_id=retry_failed.id, body=body)
        _audit(
            request,
            workspace_id=workspace_id,
            caller_sub=caller_sub,
            action="agent_intake:generation_retry_failed",
            resource_type="agent_intake",
            resource_id=retry_failed.id,
            payload={
                "agent_id": str(agent.id),
                "failure_stage": "draft_agent_plan_retry",
                "failure_message": str(exc),
            },
        )
        return {
            **agent_intake_payload(retry_failed),
            "agent": {
                **agent_payload(agent),
                "object_state": "draft",
                "state_reason": "Draft generation retry failed; retry or continue manually.",
                "state_evidence_ref": f"agent_intake/{retry_failed.id}",
            },
            "commitment": commitment.model_dump(mode="json"),
        }

    updated = build_intake_analysis(
        body=body,
        agent=agent,
        created_by=record.created_by,
        created_object_refs=refs,
    ).model_copy(update={"id": record.id, "created_at": record.created_at})
    await cp.agent_intakes.replace(updated)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_intake:generation_retry",
        resource_type="agent_intake",
        resource_id=updated.id,
        payload={
            "agent_id": str(agent.id),
            "state": updated.state,
            "readiness_score": updated.readiness["score"],
        },
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_intake:draft_objects_create",
        resource_type="agent",
        resource_id=str(agent.id),
        payload=refs,
    )
    return {
        **agent_intake_payload(updated),
        "agent": {
            **agent_payload(agent),
            "object_state": "draft",
            "state_reason": "Commitment Document is still draft.",
            "state_evidence_ref": f"commitment/{commitment.id}",
        },
        "commitment": commitment.model_dump(mode="json"),
    }


@router.post("/{workspace_id}/agent-intakes/{intake_id}/continue-manually")
async def continue_agent_intake_manually(
    request: Request,
    workspace_id: UUID,
    intake_id: str,
    body: AgentIntakeManualContinue | None = None,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        record = await cp.agent_intakes.get(workspace_id=workspace_id, intake_id=intake_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown intake: {intake_id}") from exc
    if record.state != "failed":
        raise WorkspaceError(f"intake {intake_id} is not in failed state")
    agent = await cp.agents.get(workspace_id=workspace_id, agent_id=record.agent_id)
    commitment = await cp.agent_commitments.current(agent=agent)
    notes = body.notes if body else ""
    updated = _manual_continue_intake(
        record=record,
        notes=notes,
        caller_sub=caller_sub,
    )
    await cp.agent_intakes.replace(updated)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="agent_intake:continue_manually",
        resource_type="agent_intake",
        resource_id=updated.id,
        payload={
            "agent_id": str(agent.id),
            "commitment_id": commitment.id,
            "notes": notes,
        },
    )
    return {
        **agent_intake_payload(updated),
        "agent": {
            **agent_payload(agent),
            "object_state": "draft",
            "state_reason": "Manual setup selected after draft generation failure.",
            "state_evidence_ref": f"agent_intake/{updated.id}",
        },
        "commitment": commitment.model_dump(mode="json"),
    }


@router.get("/{workspace_id}/agent-intakes/{intake_id}")
async def get_agent_intake(
    request: Request,
    workspace_id: UUID,
    intake_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        record = await cp.agent_intakes.get(workspace_id=workspace_id, intake_id=intake_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown intake: {intake_id}") from exc
    return agent_intake_payload(record)
