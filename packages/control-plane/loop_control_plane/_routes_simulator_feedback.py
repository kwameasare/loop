from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Request

from loop_control_plane._app_common import ACTIVE_WORKSPACE, CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import EvalCaseCreate, serialise_case
from loop_control_plane.simulator_feedback import (
    SimulatorRunCreate,
    SimulatorTurnRatingCreate,
    candidate_artifact_for,
    simulator_run_payload,
    simulator_turn_rating_payload,
)
from loop_control_plane.trace_search import TraceSummary

router = APIRouter(prefix="/v1/agents", tags=["SimulatorFeedback"])


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
        required_role=Role.ADMIN,
    )
    return await request.app.state.cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )


def _durable_trace_id(*, body: SimulatorRunCreate, agent_id: UUID) -> str:
    if len(body.trace_id) == 32:
        return body.trace_id
    seed = f"{agent_id}:{body.channel}:{body.prompt}:{body.final_answer}:{uuid4().hex}"
    return sha256(seed.encode("utf-8")).hexdigest()[:32]


def _channel_type_for_simulator(channel: str) -> str:
    return {
        "web": "web_chat",
        "web_chat": "web_chat",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
        "slack": "slack",
        "teams": "teams",
        "sms": "sms",
        "email": "email",
        "voice": "voice",
        "webhook": "webhook_api",
        "webhook_api": "webhook_api",
    }.get(channel, channel)


async def _channel_binding_id_for_run(
    request: Request,
    *,
    agent: Any,
    body: SimulatorRunCreate,
) -> str:
    if body.channel_binding_id:
        return body.channel_binding_id
    channel_type = _channel_type_for_simulator(body.channel)
    bindings = await request.app.state.cp.channel_bindings.list_for_agent(agent=agent)
    match = next(
        (binding for binding in bindings if binding.channel_type == channel_type),
        None,
    )
    if match is None or match.status == "not_configured":
        return ""
    return match.id


@router.post("/{agent_id}/simulator/runs", status_code=201)
async def create_simulator_run(
    request: Request,
    agent_id: UUID,
    body: SimulatorRunCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    trace_id = _durable_trace_id(body=body, agent_id=agent.id)
    channel_binding_id = await _channel_binding_id_for_run(
        request,
        agent=agent,
        body=body,
    )
    body = body.model_copy(
        update={
            "trace_id": trace_id,
            "channel_binding_id": channel_binding_id,
        }
    )
    run = await cp.simulator_feedback.add_run(
        agent=agent,
        body=body,
        actor_sub=caller_sub,
    )
    cp.trace_store.add(
        TraceSummary(
            workspace_id=workspace_id,
            trace_id=trace_id,
            turn_id=uuid4(),
            conversation_id=uuid4(),
            agent_id=agent.id,
            started_at=datetime.now(UTC),
            duration_ms=body.latency_ms,
            span_count=4,
            error=body.status == "failed",
            channel_binding_id=channel_binding_id,
        )
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="simulator_run:create",
        resource_type="simulator_run",
        store=cp.audit_events,
        resource_id=run.id,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent.id),
            "channel": body.channel,
            "trace_id": body.trace_id,
            "channel_binding_id": channel_binding_id,
            "status": body.status,
        },
    )
    return simulator_run_payload(run)


@router.get("/{agent_id}/simulator/runs")
async def list_simulator_runs(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    rows = await cp.simulator_feedback.list_runs_for_agent(agent=agent)
    return {"items": [simulator_run_payload(row) for row in rows]}


@router.post("/{agent_id}/simulator/turn-ratings", status_code=201)
async def rate_simulator_turn(
    request: Request,
    agent_id: UUID,
    body: SimulatorTurnRatingCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    candidate = candidate_artifact_for(body)
    eval_ref: dict[str, Any] | None = None
    if body.save_as_eval:
        suite = await cp.eval_suites.get_or_create_suite(
            workspace_id=workspace_id,
            name="First proof turn ratings",
            dataset_ref=f"agent:{agent.id}:first-proof",
            metrics=["behavior_match", "groundedness", "risk_handling"],
            actor_sub=caller_sub,
        )
        case = await cp.eval_suites.add_case(
            workspace_id=workspace_id,
            suite_id=suite.id,
            body=EvalCaseCreate(
                name=candidate["title"],
                input={
                    "agent_id": str(agent.id),
                    "channel": body.channel,
                    "prompt": body.prompt,
                    "trace_id": body.trace_id,
                    "simulator_run_id": body.simulator_run_id,
                    "rating": body.rating,
                    "observed_answer": body.final_answer,
                },
                expected={"outcome": candidate["expected_outcome"]},
                scorers=[
                    {
                        "kind": "llm_judge",
                        "config": {"rubric": "first proof expected outcome"},
                    },
                    {
                        "kind": "trace_assertion",
                        "config": {"trace_id": body.trace_id},
                    },
                ],
                source=f"first-proof:{body.rating}",
                source_ref=body.trace_id or body.simulator_run_id or f"agent:{agent.id}:simulator",
                attachments=[body.trace_id] if body.trace_id else [],
            ),
            actor_sub=caller_sub,
        )
        eval_ref = {
            "suite_id": str(suite.id),
            "case_id": str(case.id),
            "case": serialise_case(case),
        }

    record = await cp.simulator_feedback.add(
        agent=agent,
        body=body,
        candidate_artifact=candidate,
        eval_case_ref=eval_ref,
        actor_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="simulator_turn:rate",
        resource_type="simulator_turn_rating",
        store=cp.audit_events,
        resource_id=record.id,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent.id),
            "rating": body.rating,
            "trace_id": body.trace_id,
            "simulator_run_id": body.simulator_run_id,
            "save_as_eval": body.save_as_eval,
            "eval_case_id": eval_ref["case_id"] if eval_ref else None,
            "behavior_note_id": (
                record.behavior_note_ref["id"] if record.behavior_note_ref else None
            ),
            "few_shot_id": record.few_shot_ref["id"] if record.few_shot_ref else None,
        },
    )
    return simulator_turn_rating_payload(record)


@router.get("/{agent_id}/simulator/turn-ratings")
async def list_simulator_turn_ratings(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID = ACTIVE_WORKSPACE,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    rows = await cp.simulator_feedback.list_for_agent(agent=agent)
    return {"items": [simulator_turn_rating_payload(row) for row in rows]}
