from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_agents import AgentCreate, agent_payload
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_intake import (
    AgentIntakeCreate,
    agent_intake_payload,
    apply_enterprise_template,
    build_intake_analysis,
    template_payloads,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.channel_bindings import SUPPORTED_CHANNELS, ChannelBindingUpsert
from loop_control_plane.eval_suites import EvalCaseCreate
from loop_control_plane.memory_policies import MemoryPolicyUpsert
from loop_control_plane.tool_contracts import ToolContractUpsert

router = APIRouter(prefix="/v1/workspaces", tags=["AgentIntake"])


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


def _channel_type(value: str) -> str | None:
    normalised = "".join(ch for ch in value.lower() if ch.isalnum() or ch == "_")
    channel = _CHANNEL_ALIASES.get(normalised)
    return channel if channel in SUPPORTED_CHANNELS else None


def _tool_id(value: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")
    return f"mock_{slug or 'system'}"


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

    channel_refs: list[dict[str, str]] = []
    for requested in body.contract.channels:
        channel_type = _channel_type(requested)
        if channel_type is None:
            continue
        binding = await cp.channel_bindings.upsert(
            agent=agent,
            body=ChannelBindingUpsert(
                channel_type=channel_type,  # type: ignore[arg-type]
                display_name=requested.strip() or channel_type,
                status="draft",
                identity_config={"created_from": "agent_intake"},
            ),
        )
        channel_refs.append({"id": binding.id, "channel_type": binding.channel_type})

    tool_refs: list[dict[str, str]] = []
    for system in body.contract.systems_touched:
        if not system.strip():
            continue
        tool_id = _tool_id(system)
        contract = await cp.tool_contracts.upsert(
            agent=agent,
            tool_id=tool_id,
            body=ToolContractUpsert(
                name=f"{system.strip()} mock tool",
                description=(
                    f"Mock contract inferred from intake for {system.strip()}. "
                    "Live mode requires owner review."
                ),
                side_effect_level="read",
                sandbox_status="mock",
                owner_user_id=body.contract.owner_user_id,
                failure_behavior="Return unavailable in sandbox and preserve a trace span.",
            ),
        )
        tool_refs.append({"id": contract.id, "tool_id": contract.tool_id})

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

    refs = {
        "agent_id": str(agent.id),
        "commitment_id": commitment.id,
        "channel_bindings": channel_refs,
        "tool_contracts": tool_refs,
        "memory_policy_id": memory_policy.id,
        "eval_suite_id": str(suite.id),
        "eval_cases": eval_refs,
    }
    if body.template_id:
        refs["template_id"] = body.template_id
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
