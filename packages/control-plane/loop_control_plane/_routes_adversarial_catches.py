from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.adversarial_catches import (
    AdversarialProbeRunCreate,
    CatchResolutionCreate,
    ProbeBudgetUpdate,
    catch_payload,
    probe_run_payload,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import EvalCaseCreate

router = APIRouter(prefix="/v1/agents", tags=["AdversarialCatches"])
workspace_router = APIRouter(prefix="/v1/workspaces", tags=["AdversarialCatches"])


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
    return await cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
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
        resource_type="adversarial_catch",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@workspace_router.get("/{workspace_id}/adversarial-probe-budgets")
async def get_adversarial_probe_budgets(
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
    record = await cp.adversarial_catches.get_budgets(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
    )
    return record.model_dump(mode="json")


@workspace_router.patch("/{workspace_id}/adversarial-probe-budgets")
async def update_adversarial_probe_budgets(
    request: Request,
    workspace_id: UUID,
    body: ProbeBudgetUpdate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    record = await cp.adversarial_catches.update_budgets(
        workspace_id=workspace_id,
        body=body,
        actor_sub=caller_sub,
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="adversarial_probe:budget_update",
        resource_type="adversarial_probe_budget",
        resource_id=str(workspace_id),
        store=cp.audit_events,
        request_id=request_id(request),
        payload={"budgets": record.budgets},
    )
    return record.model_dump(mode="json")


@router.post("/{agent_id}/adversarial-probes/run", status_code=201)
async def run_adversarial_probe(
    request: Request,
    agent_id: UUID,
    body: AdversarialProbeRunCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    run, catches = await cp.adversarial_catches.run_probe(
        agent=agent,
        body=body,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="adversarial_probe:run",
        resource_id=run.id,
        payload={
            "agent_id": str(agent.id),
            "rule_id": body.rule_id,
            "risk_class": body.risk_class,
            "catch_count": len(catches),
        },
    )
    return {
        "run": probe_run_payload(run),
        "catches": [catch_payload(catch) for catch in catches],
    }


@router.get("/{agent_id}/catches")
async def list_catches(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
    )
    rows = await cp.adversarial_catches.list_for_agent(agent=agent)
    return {"items": [catch_payload(row) for row in rows]}


@router.post("/{agent_id}/catches/{catch_id}/resolve")
async def resolve_catch(
    request: Request,
    agent_id: UUID,
    catch_id: str,
    body: CatchResolutionCreate,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    cp = request.app.state.cp
    agent = await _agent(
        request,
        agent_id=agent_id,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    workspace_id = agent.workspace_id
    catches = await cp.adversarial_catches.list_for_agent(agent=agent)
    current = next((item for item in catches if item.id == catch_id), None)
    if current is None:
        # Let the registry raise the domain-shaped error.
        current = await cp.adversarial_catches.resolve(
            agent=agent,
            catch_id=catch_id,
            body=body,
            eval_case_refs=[],
            actor_sub=caller_sub,
        )
        return catch_payload(current)

    eval_refs: list[dict[str, str]] = []
    if body.create_eval_cases and not body.dismiss_reason:
        suite = await cp.eval_suites.get_or_create_suite(
            workspace_id=workspace_id,
            name="Adversarial catches",
            dataset_ref=f"agent:{agent.id}:adversarial-catches",
            metrics=["behavior_match", "risk_handling", "regression_guard"],
            actor_sub=caller_sub,
        )
        for label, expected in (
            ("accepted interpretation", body.intended_interpretation),
            ("rejected interpretation", body.rejected_interpretation),
        ):
            if not expected.strip():
                continue
            case = await cp.eval_suites.add_case(
                workspace_id=workspace_id,
                suite_id=suite.id,
                body=EvalCaseCreate(
                    name=f"Catch {current.id}: {label}",
                    input={
                        "rule_id": current.rule_id,
                        "rule_text": current.rule_text,
                        "scenario": current.generated_scenario,
                        "question": current.question,
                    },
                    expected={
                        "outcome": expected,
                        "proposed_patch": body.proposed_patch,
                    },
                    scorers=[
                        {
                            "kind": "llm_judge",
                            "config": {"rubric": "adversarial catch interpretation"},
                        }
                    ],
                    source="adversarial_catch",
                    source_ref=current.evidence_ref,
                    attachments=[current.evidence_ref],
                ),
                actor_sub=caller_sub,
            )
            eval_refs.append({"suite_id": str(suite.id), "case_id": str(case.id)})

    resolved = await cp.adversarial_catches.resolve(
        agent=agent,
        catch_id=catch_id,
        body=body,
        eval_case_refs=eval_refs,
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="adversarial_catch:resolve",
        resource_id=resolved.id,
        payload={
            "agent_id": str(agent.id),
            "status": resolved.status,
            "eval_cases": eval_refs,
            "proposed_patch": body.proposed_patch,
        },
    )
    return catch_payload(resolved)
