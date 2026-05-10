"""Workspace eval suite + run routes (P0.4).

* ``GET   /v1/workspaces/{id}/eval-suites`` (any member)
* ``POST  /v1/workspaces/{id}/eval-suites`` (ADMIN)
* ``GET   /v1/eval-suites/{id}``            (any member)
* ``GET   /v1/eval-suites/{id}/runs``       (any member)
* ``POST  /v1/eval-suites/{id}/runs``       (ADMIN)
* ``GET   /v1/eval-runs/{id}``              (any member)
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
router_runs = APIRouter(prefix="/v1/eval-runs", tags=["Evals"])


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
    sentence_role: str | None = Field(default=None, max_length=64)
    trace_id: str = Field(min_length=1, max_length=512)
    failure_reason: str = Field(min_length=1, max_length=1024)
    expected_outcome: str = Field(min_length=1, max_length=4096)
    proposed_fix: str = Field(min_length=1, max_length=4096)
    replay_ref: str = Field(default="replay/not-run", max_length=512)
    source: str = Field(default="behavior-fix", max_length=128)
    channel: str | None = Field(default=None, max_length=64)
    version_ref: str | None = Field(default=None, max_length=256)
    risk_tags: list[str] = Field(default_factory=list, max_length=32)
    target_object_kind: str | None = Field(default=None, max_length=128)


class ObservedFailureRepairBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str = Field(min_length=1, max_length=256)
    sentence_text: str = Field(min_length=1, max_length=4096)
    sentence_role: str | None = Field(default=None, max_length=64)
    trace_id: str = Field(min_length=1, max_length=512)
    failure_reason: str = Field(min_length=1, max_length=1024)
    replay_ref: str = Field(default="replay/not-run", max_length=512)
    risk_tags: list[str] = Field(default_factory=list, max_length=32)
    target_object_kind: str | None = Field(default=None, max_length=128)


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


def _agent_id_from_dataset_ref(dataset_ref: str) -> str | None:
    if not dataset_ref.startswith("agent:"):
        return None
    parts = dataset_ref.split(":")
    return parts[1] if len(parts) >= 2 and parts[1] else None


async def _suite_summary(request: Request, workspace_id: UUID, suite: Any) -> dict[str, Any]:
    cp = request.app.state.cp
    cases = await cp.eval_suites.list_cases(workspace_id=workspace_id, suite_id=suite.id)
    runs = await cp.eval_suites.list_runs(workspace_id=workspace_id, suite_id=suite.id)
    latest = runs[0] if runs else None
    payload = serialise_suite(suite)
    payload["agent_id"] = _agent_id_from_dataset_ref(suite.dataset_ref)
    payload["cases"] = len(cases)
    payload["case_count"] = len(cases)
    payload["last_run_at"] = (
        (latest.completed_at or latest.started_at).isoformat() if latest else None
    )
    payload["pass_rate"] = (
        latest.metrics.get("pass_rate") if latest and "pass_rate" in latest.metrics else None
    )
    return payload


def _run_counts(run: Any) -> dict[str, int]:
    return {
        "passed": int(run.metrics.get("passed", 0)),
        "failed": int(run.metrics.get("failed", 0)),
        "errored": int(run.metrics.get("errored", 0)),
        "total": int(run.metrics.get("total", 0)),
    }


def _run_summary(run: Any) -> dict[str, Any]:
    payload = serialise_run(run)
    payload.update(_run_counts(run))
    payload["baseline_run_id"] = None
    return payload


def _responsible_object_kind(
    sentence_text: str,
    *,
    sentence_role: str | None = None,
    explicit_kind: str | None = None,
) -> str:
    if explicit_kind:
        return explicit_kind
    text = sentence_text.lower()
    if sentence_role == "tool" or "tool" in text:
        return "tool_contract"
    if sentence_role == "memory" or "memory" in text:
        return "memory_policy"
    if "knowledge" in text or "cite" in text or "policy" in text:
        return "knowledge_chunk"
    if any(
        channel in text
        for channel in (
            "channel",
            "whatsapp",
            "telegram",
            "slack",
            "sms",
            "voice",
            "email",
        )
    ):
        return "channel_constraint"
    return "behavior_sentence"


def _responsible_object_label(kind: str) -> str:
    return {
        "tool_contract": "Responsible tool contract",
        "memory_policy": "Responsible memory policy",
        "knowledge_chunk": "Responsible knowledge source",
        "channel_constraint": "Responsible channel constraint",
        "behavior_sentence": "Responsible behavior sentence",
    }.get(kind, "Responsible object")


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
    return {"items": [await _suite_summary(request, workspace_id, s) for s in rows]}


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
    return await _suite_summary(request, workspace_id, suite)


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
    target_kind = _responsible_object_kind(
        body.sentence_text,
        sentence_role=body.sentence_role,
        explicit_kind=body.target_object_kind,
    )
    target_object = {
        "kind": target_kind,
        "id": body.sentence_id,
        "label": _responsible_object_label(target_kind),
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
            "sentence_role": body.sentence_role,
            "target_object_kind": target_kind,
            "trace_id": body.trace_id,
            "replay_ref": body.replay_ref,
            "risk_tags": body.risk_tags,
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
    target_kind = _responsible_object_kind(
        body.sentence_text,
        sentence_role=body.sentence_role,
        explicit_kind=body.target_object_kind,
    )
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
                "sentence_role": body.sentence_role,
                "trace_id": body.trace_id,
                "failure_reason": body.failure_reason,
                "replay_ref": body.replay_ref,
                "channel": body.channel,
                "version_ref": body.version_ref,
                "risk_tags": body.risk_tags,
                "target_object_kind": target_kind,
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
            "sentence_role": body.sentence_role,
            "target_object_kind": target_kind,
            "trace_id": body.trace_id,
            "replay_ref": body.replay_ref,
            "channel": body.channel,
            "version_ref": body.version_ref,
            "risk_tags": body.risk_tags,
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


@router_suites.get("/{suite_id}")
async def get_suite(
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
        suite = await cp.eval_suites.get_suite(workspace_id=workspace_id, suite_id=suite_id)
        runs = await cp.eval_suites.list_runs(workspace_id=workspace_id, suite_id=suite_id)
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = await _suite_summary(request, workspace_id, suite)
    run_items = [_run_summary(run) for run in runs]
    for index, run in enumerate(run_items):
        if index + 1 < len(run_items):
            run["baseline_run_id"] = run_items[index + 1]["id"]
    payload["runs"] = run_items
    return payload


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
    items = [_run_summary(r) for r in rows]
    for index, run in enumerate(items):
        if index + 1 < len(items):
            run["baseline_run_id"] = items[index + 1]["id"]
    return {"items": items}


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


@router_runs.get("/{run_id}")
async def get_run(
    request: Request,
    run_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    try:
        run = await cp.eval_suites.get_run(run_id=run_id)
    except EvalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=run.workspace_id,
        user_sub=caller_sub,
    )
    payload = _run_summary(run)
    payload["cases"] = []
    return payload


__all__ = ["router_agents", "router_runs", "router_suites", "router_workspaces"]
