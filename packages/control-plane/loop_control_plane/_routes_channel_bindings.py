from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from loop_control_plane._agent_route_utils import resolve_agent_for_route
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role
from loop_control_plane.channel_bindings import (
    SUPPORTED_CHANNELS,
    ChannelActivityCreate,
    ChannelBindingRecord,
    ChannelBindingUpsert,
    ChannelPreviewEvalCaseCreate,
    ChannelPreviewMatrixRequest,
    ChannelReadinessUpdate,
    channel_binding_payload,
    channel_readiness_state,
)
from loop_control_plane.eval_suites import EvalCaseCreate, serialise_case

router = APIRouter(prefix="/v1/agents", tags=["ChannelBindings"])


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    return await resolve_agent_for_route(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=required_role,
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
        resource_type="channel_binding",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


def _compact_expected(expected: str, *, limit: int) -> str:
    text = " ".join(expected.split())
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}..."


def _channel_preview_text(
    *,
    channel_type: str,
    scenario_title: str,
    user_message: str,
    expected_outcome: str,
) -> str:
    compact = _compact_expected(expected_outcome, limit=140)
    if channel_type == "web_chat":
        return f"{compact}\n\nActions: [Open invoice] [Escalate]"
    if channel_type == "whatsapp":
        return f"{compact}\n\nReply 1 to verify the charge, 2 to escalate."
    if channel_type == "telegram":
        return f"{compact}\n\nUse /status for the case summary or /agent for a teammate."
    if channel_type == "slack":
        return f"Thread reply for {scenario_title}: {compact}\nButtons: Verify account · Escalate"
    if channel_type == "teams":
        return f"Teams thread: {compact}\nAdaptive card actions: Verify account · Escalate"
    if channel_type == "sms":
        return _compact_expected(expected_outcome, limit=180)
    if channel_type == "email":
        return (
            f"Subject: {scenario_title}\n\n"
            f"Thanks for the context.\n\n{expected_outcome}\n\n"
            "Case summary and next steps are included for auditability."
        )
    if channel_type == "voice":
        return (
            f"Spoken answer: {compact} Then confirm: would you like me to connect you to support?"
        )
    return (
        "{\n"
        f'  "scenario": "{scenario_title}",\n'
        f'  "user_message": "{user_message}",\n'
        f'  "expected_outcome": "{compact}"\n'
        "}"
    )


def _channel_constraints(channel_type: str) -> list[str]:
    return {
        "web_chat": ["Can show links and buttons", "Supports longer answer blocks"],
        "whatsapp": ["Template-safe language", "Short numbered options", "Opt-in required"],
        "telegram": ["Command-aware copy", "Group/direct policy matters"],
        "slack": ["Thread-safe reply", "Mention policy applies"],
        "teams": ["Thread-safe reply", "Tenant permissions apply"],
        "sms": ["Short copy", "Opt-out language", "No rich controls"],
        "email": ["Full explanation allowed", "Signature and SLA policy apply"],
        "voice": ["Short spoken turns", "Confirmation prompts", "Barge-in policy"],
        "webhook_api": ["Signed JSON", "Idempotency required", "Retry policy applies"],
    }[channel_type]


def _channel_notes(channel_type: str) -> list[str]:
    return {
        "web_chat": ["Keeps action buttons visible next to the answer."],
        "whatsapp": ["Compresses the answer and presents numbered choices."],
        "telegram": ["Adds command affordances without changing agent behavior."],
        "slack": ["Renders as an internal thread with explicit action buttons."],
        "teams": ["Uses an adaptive-card style action set."],
        "sms": ["Strips rich controls and keeps the reply short."],
        "email": ["Expands into a fuller case summary."],
        "voice": ["Turns the answer into a short spoken confirmation loop."],
        "webhook_api": ["Exposes the same decision as structured JSON."],
    }[channel_type]


def _formatting_failures(
    *,
    binding: ChannelBindingRecord,
    rendered_preview: str,
    expected_outcome: str,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if binding.status == "not_configured":
        failures.append(
            {
                "id": f"{binding.channel_type}_not_configured",
                "severity": "blocker",
                "message": f"{binding.display_name} is not configured, so this scenario cannot ship on that channel.",
                "expected_outcome": "Configure the channel binding before production rollout.",
            }
        )
    readiness = channel_readiness_state(binding)
    if readiness in {"blocked", "needs_readiness"}:
        failures.append(
            {
                "id": f"{binding.channel_type}_readiness_incomplete",
                "severity": "warning",
                "message": f"{binding.display_name} readiness is {readiness.replace('_', ' ')}.",
                "expected_outcome": "Complete readiness checks before promoting this channel.",
            }
        )
    if binding.channel_type == "sms" and len(rendered_preview) > 160:
        failures.append(
            {
                "id": "sms_too_long",
                "severity": "warning",
                "message": "SMS preview exceeds 160 characters; split or compress the response.",
                "expected_outcome": _compact_expected(expected_outcome, limit=140),
            }
        )
    if binding.channel_type == "voice" and len(rendered_preview) > 240:
        failures.append(
            {
                "id": "voice_too_verbose",
                "severity": "warning",
                "message": "Voice answer is too long for a low-latency spoken turn.",
                "expected_outcome": "Shorten the answer and ask one confirmation question.",
            }
        )
    return failures


def _matrix_row(
    *,
    binding: ChannelBindingRecord,
    body: ChannelPreviewMatrixRequest,
) -> dict[str, Any]:
    rendered_preview = _channel_preview_text(
        channel_type=binding.channel_type,
        scenario_title=body.scenario_title,
        user_message=body.user_message,
        expected_outcome=body.expected_outcome,
    )
    failures = _formatting_failures(
        binding=binding,
        rendered_preview=rendered_preview,
        expected_outcome=body.expected_outcome,
    )
    return {
        "binding_id": binding.id,
        "channel_type": binding.channel_type,
        "display_name": binding.display_name,
        "provider": binding.provider,
        "binding_status": binding.status,
        "readiness_state": channel_readiness_state(binding),
        "rendered_preview": rendered_preview,
        "adaptation_notes": _channel_notes(binding.channel_type),
        "constraints": _channel_constraints(binding.channel_type),
        "formatting_failures": failures,
        "eval_case_seed": {
            "scenario_title": body.scenario_title,
            "channel_type": binding.channel_type,
            "binding_id": binding.id,
            "user_message": body.user_message,
            "rendered_preview": rendered_preview,
            "expected_outcome": body.expected_outcome,
            "failure_reason": failures[0]["message"] if failures else "",
            "source_ref": f"channel-preview/{binding.id}/{body.scenario_title}",
        },
    }


@router.get("/{agent_id}/channel-bindings")
async def list_channel_bindings(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    bindings = await request.app.state.cp.channel_bindings.list_for_agent(agent=agent)
    return {"items": [channel_binding_payload(binding) for binding in bindings]}


@router.post("/{agent_id}/channel-bindings", status_code=201)
async def upsert_channel_binding(
    request: Request,
    agent_id: UUID,
    body: ChannelBindingUpsert,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    binding = await request.app.state.cp.channel_bindings.upsert(
        agent=agent,
        body=body,
    )
    invalidated = await request.app.state.cp.preapproved_classes.invalidate_for_change_types(
        agent=agent,
        change_types=["channel"],
        reason=f"Channel binding {binding.id} changed.",
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:upsert",
        resource_id=binding.id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": binding.channel_type,
            "status": binding.status,
            "invalidated_pre_approved_classes": [
                record.id for record in invalidated
            ],
        },
    )
    return channel_binding_payload(binding)


@router.post("/{agent_id}/channel-bindings/{binding_id}/activity")
async def record_channel_activity(
    request: Request,
    agent_id: UUID,
    binding_id: str,
    body: ChannelActivityCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    binding = await request.app.state.cp.channel_bindings.record_activity(
        agent=agent,
        binding_id=binding_id,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:activity",
        resource_id=binding.id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": binding.channel_type,
            "trace_id": body.trace_id,
            "status": body.status,
            "failure_message": body.failure_message,
        },
    )
    return channel_binding_payload(binding)


@router.post("/{agent_id}/channel-bindings/preview-matrix")
async def preview_channel_matrix(
    request: Request,
    agent_id: UUID,
    body: ChannelPreviewMatrixRequest,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    bindings = await request.app.state.cp.channel_bindings.list_for_agent(agent=agent)
    selected = set(body.channel_types or [])
    if not selected:
        selected = {
            binding.channel_type for binding in bindings if binding.status != "not_configured"
        }
    if not selected:
        selected = set(SUPPORTED_CHANNELS)
    rows = [
        _matrix_row(binding=binding, body=body)
        for binding in bindings
        if binding.channel_type in selected
    ]
    return {
        "agent_id": str(agent_id),
        "scenario_title": body.scenario_title,
        "user_message": body.user_message,
        "expected_outcome": body.expected_outcome,
        "rows": rows,
        "summary": {
            "channels": len(rows),
            "formatting_failures": sum(len(row["formatting_failures"]) for row in rows),
            "ready_channels": sum(1 for row in rows if row["readiness_state"] == "ready"),
        },
    }


@router.post("/{agent_id}/channel-bindings/preview-matrix/eval-cases", status_code=201)
async def create_channel_preview_eval_case(
    request: Request,
    agent_id: UUID,
    body: ChannelPreviewEvalCaseCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    suite = await request.app.state.cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name="Channel formatting failures",
        dataset_ref="channel-formatting-failures",
        metrics=["channel_format", "policy_adherence", "regression_guard"],
        actor_sub=caller_sub,
    )
    case = await request.app.state.cp.eval_suites.add_case(
        workspace_id=workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=f"{body.channel_type} formatting: {body.scenario_title}",
            input={
                "agent_id": str(agent_id),
                "channel_type": body.channel_type,
                "binding_id": body.binding_id,
                "user_message": body.user_message,
                "rendered_preview": body.rendered_preview,
                "source_ref": body.source_ref,
            },
            expected={
                "outcome": body.expected_outcome,
                "formatting_fix": body.failure_reason,
            },
            scorers=[
                {
                    "kind": "channel_format",
                    "config": {"channel_type": body.channel_type},
                },
                {
                    "kind": "llm_judge",
                    "config": {"rubric": "channel-specific answer adaptation"},
                },
            ],
            source="channel-preview-matrix",
            source_ref=body.source_ref,
            attachments=[body.binding_id, body.channel_type],
        ),
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:preview_eval_case",
        resource_id=body.binding_id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": body.channel_type,
            "case_id": str(case.id),
            "suite_id": str(suite.id),
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "case": serialise_case(case),
    }


@router.post("/{agent_id}/channel-bindings/{binding_id}/readiness/{check_id}")
async def update_channel_readiness(
    request: Request,
    agent_id: UUID,
    binding_id: str,
    check_id: str,
    body: ChannelReadinessUpdate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    binding = await request.app.state.cp.channel_bindings.set_readiness(
        agent=agent,
        binding_id=binding_id,
        check_id=check_id,
        body=body,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="channel_binding:readiness",
        resource_id=binding.id,
        payload={
            "agent_id": str(agent_id),
            "channel_type": binding.channel_type,
            "check_id": check_id,
            "status": body.status,
        },
    )
    return channel_binding_payload(binding)
