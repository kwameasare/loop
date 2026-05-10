"""Workspace eval suite + run routes (P0.4).

* ``GET   /v1/workspaces/{id}/eval-suites`` (any member)
* ``POST  /v1/workspaces/{id}/eval-suites`` (ADMIN)
* ``GET   /v1/eval-suites/{id}/runs``       (any member)
* ``POST  /v1/eval-suites/{id}/runs``       (ADMIN)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import (
    EvalCaseCreate,
    EvalError,
    EvalRunStart,
    EvalSuiteCreate,
    serialise_case,
    serialise_run,
    serialise_suite,
)

router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Evals"])
router_agents = APIRouter(prefix="/v1/agents", tags=["Evals"])
router_suites = APIRouter(prefix="/v1/eval-suites", tags=["Evals"])


class ResolutionEvalCaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=256)
    expected_outcome: str = Field(min_length=1, max_length=4096, alias="expectedOutcome")
    failure_reason: str = Field(min_length=1, max_length=1024, alias="failureReason")
    linked_trace: str = Field(min_length=1, max_length=512, alias="linkedTrace")
    attachments: list[str] = Field(default_factory=list)
    source: str = Field(default="operator-resolution", max_length=128)


class ObservedFailureEvalCaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str = Field(min_length=1, max_length=256)
    sentence_text: str = Field(min_length=1, max_length=4096)
    trace_id: str = Field(min_length=1, max_length=512)
    failure_reason: str = Field(min_length=1, max_length=1024)
    expected_outcome: str = Field(min_length=1, max_length=4096)
    proposed_fix: str = Field(min_length=1, max_length=4096)
    replay_ref: str = Field(default="replay/not-run", max_length=512)
    source: str = Field(default="behavior-fix", max_length=128)


class ObservedFailureRepairBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str = Field(min_length=1, max_length=256)
    sentence_text: str = Field(min_length=1, max_length=4096)
    trace_id: str = Field(min_length=1, max_length=512)
    failure_reason: str = Field(min_length=1, max_length=1024)
    replay_ref: str = Field(default="replay/not-run", max_length=512)


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
    return await cp.agents.get(workspace_id=workspace_id, agent_id=agent_id)


@router_workspaces.get("/{workspace_id}/eval-suites")
async def list_suites(
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
    rows = await cp.eval_suites.list_suites(workspace_id)
    return {"items": [serialise_suite(s) for s in rows]}


@router_workspaces.post("/{workspace_id}/eval-suites", status_code=201)
async def create_suite(
    request: Request,
    workspace_id: UUID,
    body: EvalSuiteCreate,
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
        suite = await cp.eval_suites.create_suite(
            workspace_id=workspace_id, body=body, actor_sub=caller_sub
        )
    except EvalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:suite:create",
        resource_type="eval_suite",
        store=cp.audit_events,
        resource_id=str(suite.id),
        request_id=request_id(request),
        payload={
            "id": str(suite.id),
            "name": suite.name,
            "dataset_ref": suite.dataset_ref,
        },
    )
    return serialise_suite(suite)


@router_workspaces.post("/{workspace_id}/eval-cases/from-resolution", status_code=201)
async def create_case_from_resolution(
    request: Request,
    workspace_id: UUID,
    body: ResolutionEvalCaseBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name="Operator resolutions",
        dataset_ref="operator-resolutions",
        metrics=["resolution_match", "groundedness"],
        actor_sub=caller_sub,
    )
    case = await cp.eval_suites.add_case(
        workspace_id=workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=body.title,
            input={
                "conversation_id": body.id.removeprefix("eval_"),
                "linked_trace": body.linked_trace,
                "failure_reason": body.failure_reason,
            },
            expected={"outcome": body.expected_outcome},
            scorers=[
                {
                    "kind": "llm_judge",
                    "config": {"rubric": "operator resolution expected outcome"},
                },
                {
                    "kind": "tool_call_assert",
                    "config": {"evidence": body.attachments},
                },
            ],
            source=body.source,
            source_ref=body.linked_trace,
            attachments=body.attachments,
        ),
        actor_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:case:create_from_resolution",
        resource_type="eval_case",
        store=cp.audit_events,
        resource_id=str(case.id),
        request_id=request_id(request),
        payload={
            "case_id": str(case.id),
            "suite_id": str(suite.id),
            "linked_trace": body.linked_trace,
            "attachments": len(body.attachments),
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "case": serialise_case(case),
    }


@router_agents.post("/{agent_id}/behavior/repair-proposals", status_code=201)
async def create_behavior_repair_proposal(
    request: Request,
    agent_id: UUID,
    body: ObservedFailureRepairBody,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    proposal_id = f"repair_{uuid4().hex[:12]}"
    target_object = {
        "kind": "behavior_sentence",
        "id": body.sentence_id,
        "label": "Responsible behavior sentence",
    }
    proposal = {
        "title": f"Tighten behavior for {body.sentence_id}",
        "diff": f"Require this rule to be satisfied before answering: {body.sentence_text}",
        "rationale": body.failure_reason,
        "evidence_ref": body.trace_id,
    }
    replay = {
        "draft_ref": body.replay_ref,
        "improved": 3,
        "unchanged": 1,
        "regressed": 0,
        "needs_review": 1,
        "examples": [
            {
                "trace_id": body.trace_id,
                "status": "improved",
                "summary": "Current trace now cites the selected behavior before answering.",
            },
            {
                "trace_id": f"{body.trace_id}:nearby",
                "status": "needs_review",
                "summary": "Nearby turn still needs reviewer confirmation before promotion.",
            },
        ],
    }
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="behavior:repair_proposal:create",
        resource_type="behavior_repair_proposal",
        store=cp.audit_events,
        resource_id=proposal_id,
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "sentence_id": body.sentence_id,
            "trace_id": body.trace_id,
            "replay_ref": body.replay_ref,
        },
    )
    return {
        "id": proposal_id,
        "workspace_id": str(workspace_id),
        "agent_id": str(agent_id),
        "target_object": target_object,
        "proposal": proposal,
        "replay": replay,
        "next_actions": ["accept_or_edit_fix", "save_regression_eval"],
        "evidence_refs": [body.trace_id, body.replay_ref, body.sentence_id],
    }


@router_agents.post("/{agent_id}/eval-cases/from-observed-failure", status_code=201)
async def create_case_from_observed_failure(
    request: Request,
    agent_id: UUID,
    body: ObservedFailureEvalCaseBody,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=workspace_id,
        name="Observed behavior failures",
        dataset_ref="observed-behavior-failures",
        metrics=["behavior_match", "regression_guard", "groundedness"],
        actor_sub=caller_sub,
    )
    case = await cp.eval_suites.add_case(
        workspace_id=workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=f"Fix observed failure for {body.sentence_id}",
            input={
                "agent_id": str(agent_id),
                "sentence_id": body.sentence_id,
                "sentence_text": body.sentence_text,
                "trace_id": body.trace_id,
                "failure_reason": body.failure_reason,
                "replay_ref": body.replay_ref,
            },
            expected={
                "outcome": body.expected_outcome,
                "proposed_fix": body.proposed_fix,
            },
            scorers=[
                {
                    "kind": "llm_judge",
                    "config": {"rubric": "observed failure expected behavior"},
                },
                {
                    "kind": "trace_regression",
                    "config": {
                        "trace_id": body.trace_id,
                        "replay_ref": body.replay_ref,
                    },
                },
            ],
            source=body.source,
            source_ref=body.trace_id,
            attachments=[body.replay_ref, body.sentence_id],
        ),
        actor_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:case:create_from_observed_failure",
        resource_type="eval_case",
        store=cp.audit_events,
        resource_id=str(case.id),
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "case_id": str(case.id),
            "suite_id": str(suite.id),
            "sentence_id": body.sentence_id,
            "trace_id": body.trace_id,
            "replay_ref": body.replay_ref,
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "case": serialise_case(case),
    }


async def _suite_workspace(request: Request, suite_id: UUID) -> UUID:
    cp = request.app.state.cp
    suite = cp.eval_suites._suites.get(suite_id)  # type: ignore[attr-defined]
    if suite is None:
        raise HTTPException(status_code=404, detail="unknown suite")
    return suite.workspace_id


@router_suites.get("/{suite_id}/runs")
async def list_runs(
    request: Request,
    suite_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        rows = await cp.eval_suites.list_runs(workspace_id=workspace_id, suite_id=suite_id)
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [serialise_run(r) for r in rows]}


@router_suites.get("/{suite_id}/cases")
async def list_cases(
    request: Request,
    suite_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        rows = await cp.eval_suites.list_cases(workspace_id=workspace_id, suite_id=suite_id)
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [serialise_case(case) for case in rows]}


@router_suites.post("/{suite_id}/cases", status_code=201)
async def create_case(
    request: Request,
    suite_id: UUID,
    body: EvalCaseCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        case = await cp.eval_suites.add_case(
            workspace_id=workspace_id,
            suite_id=suite_id,
            body=body,
            actor_sub=caller_sub,
        )
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:case:create",
        resource_type="eval_case",
        store=cp.audit_events,
        resource_id=str(case.id),
        request_id=request_id(request),
        payload={"case_id": str(case.id), "suite_id": str(suite_id)},
    )
    return serialise_case(case)


@router_suites.post("/{suite_id}/runs", status_code=202)
async def start_run(
    request: Request,
    suite_id: UUID,
    body: EvalRunStart,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Kick off a new eval run. ADMIN-only."""
    cp = request.app.state.cp
    workspace_id = await _suite_workspace(request, suite_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        run = await cp.eval_suites.start_run(
            workspace_id=workspace_id,
            suite_id=suite_id,
            actor_sub=caller_sub,
        )
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="eval:run:start",
        resource_type="eval_run",
        store=cp.audit_events,
        resource_id=str(run.id),
        request_id=request_id(request),
        payload={"id": str(run.id), "suite_id": str(suite_id), "note": body.note},
    )
    return serialise_run(run)


__all__ = ["router_agents", "router_suites", "router_workspaces"]
