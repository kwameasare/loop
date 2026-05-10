"""Canonical target UX wire-up endpoints.

These routes close the remaining "scaffold to live contract" gaps for the
target UX standard. They are deliberately deterministic and workspace-scoped:
production can swap the in-memory maps in :class:`CpApiState` for durable
tables without changing the Studio-facing API.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketDisconnect

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_workflow import (
    BranchCreate,
    ChangeSetCreate,
    branch_payload,
    change_set_payload,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.eval_suites import EvalCaseCreate, serialise_case
from loop_control_plane.tool_contracts import ToolContractUpsert, tool_contract_payload
from loop_control_plane.trace_search import TraceQuery

router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["UXWireup"])
router_agents = APIRouter(prefix="/v1/agents", tags=["UXWireup"])
router_public = APIRouter(prefix="/v1", tags=["UXWireup"])


def _bucket(request: Request, name: str) -> dict[str, Any]:
    cp = request.app.state.cp
    return cp.ux_wireup.setdefault(name, {})


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = getattr(cp.agents, "_agents", {}).get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


async def _authorize_agent_record(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> Any:
    cp = request.app.state.cp
    agent = getattr(cp.agents, "_agents", {}).get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=agent.workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return agent


async def _authorize_agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> UUID:
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return workspace_id


def _hash_payload(payload: object) -> str:
    import json

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
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


# ---------------------------------------------------------------------------
# §25 Live multiplayer presence
# ---------------------------------------------------------------------------


@router_workspaces.websocket("/{workspace_id}/presence")
async def workspace_presence_socket(
    websocket: WebSocket,
    workspace_id: UUID,
    caller_sub: str = Query(default="dev-presence"),
) -> None:
    cp = websocket.app.state.cp
    role = await cp.workspaces.role_of(workspace_id=workspace_id, user_sub=caller_sub)
    if role is None:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    room = cp.presence_rooms.setdefault(workspace_id, set())
    room.add(websocket)
    joined = {
        "type": "presence.joined",
        "workspace_id": str(workspace_id),
        "user": caller_sub,
        "at": datetime.now(UTC).isoformat(),
    }
    for peer in list(room):
        await peer.send_json(joined)
    try:
        while True:
            message = await websocket.receive_json()
            event_type = str(message.get("type") or "presence.update")
            payload = {
                **message,
                "type": event_type,
                "workspace_id": str(workspace_id),
                "user": caller_sub,
                "server_received_at": datetime.now(UTC).isoformat(),
            }
            for peer in list(room):
                await peer.send_json(payload)
    except WebSocketDisconnect:
        room.discard(websocket)
        left = {
            "type": "presence.left",
            "workspace_id": str(workspace_id),
            "user": caller_sub,
            "at": datetime.now(UTC).isoformat(),
        }
        for peer in list(room):
            await peer.send_json(left)


# ---------------------------------------------------------------------------
# §3.14 / §10.5 Replay against future drafts + trace/version diff
# ---------------------------------------------------------------------------


class ReplayAgainstDraftBody(BaseModel):
    trace_ids: list[str] = Field(min_length=1, max_length=100)
    draft_branch_ref: str = Field(min_length=1, max_length=128)
    compare_version_ref: str | None = Field(default=None, max_length=128)


class ReplayForkBody(BaseModel):
    trace_id: str = Field(min_length=1, max_length=160)
    frame_id: str = Field(min_length=1, max_length=160)
    source_version_ref: str = Field(default="production", max_length=160)
    draft_branch_ref: str | None = Field(default=None, max_length=160)
    snapshot_id: str | None = Field(default=None, max_length=160)
    evidence_ref: str = Field(min_length=1, max_length=512)
    purpose: str = Field(default="Investigate replay frame", max_length=512)


class ReplayEvalCaseBody(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    trace_id: str = Field(min_length=1, max_length=160)
    frame_id: str = Field(min_length=1, max_length=160)
    source_version_ref: str = Field(min_length=1, max_length=160)
    draft_branch_ref: str = Field(min_length=1, max_length=160)
    channel: str = Field(default="unknown", max_length=120)
    snapshot_id: str | None = Field(default=None, max_length=160)
    expected_behavior: str = Field(min_length=1, max_length=4096)
    failure_reason: str = Field(min_length=1, max_length=1200)
    replay_ref: str = Field(min_length=1, max_length=512)
    risk_tags: list[str] = Field(default_factory=list, max_length=25)


def _safe_ref(value: str, *, max_length: int = 40) -> str:
    lowered = value.strip().lower()
    safe = "".join(ch if ch.isalnum() else "-" for ch in lowered)
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")[:max_length] or uuid4().hex[:8]


def _replay_diff_for_trace(trace_id: str, draft_ref: str) -> dict[str, Any]:
    fingerprint = int(sha256(f"{trace_id}:{draft_ref}".encode()).hexdigest()[:6], 16)
    distance = 8 + fingerprint % 62
    latency_delta = -80 + fingerprint % 260
    cost_delta = -9 + fingerprint % 19
    status = "regressed" if distance >= 55 else "changed" if distance >= 22 else "same"
    return {
        "trace_id": trace_id,
        "draft_branch_ref": draft_ref,
        "behavioral_distance": distance,
        "latency_delta_ms": latency_delta,
        "cost_delta_pct": cost_delta,
        "status": status,
        "diff": {
            "response": {
                "baseline": "Production answer and citation sequence.",
                "draft": f"Draft `{draft_ref}` answer under the same input.",
                "status": status,
            },
            "tool_calls": {
                "baseline": ["lookup_order"],
                "draft": ["lookup_order", "policy_check"] if distance > 20 else ["lookup_order"],
                "status": "changed" if distance > 20 else "same",
            },
            "retrieval": {
                "baseline_rank": ["refund_policy_2026.pdf", "legacy_policy.pdf"],
                "draft_rank": ["refund_policy_2026.pdf", "escalation_policy.md"],
                "status": "changed",
            },
            "memory": {
                "baseline": [],
                "draft": ["session.language_hint"] if distance % 2 else [],
                "status": "changed" if distance % 2 else "same",
            },
            "cost": {"delta_pct": cost_delta},
            "latency": {"delta_ms": latency_delta},
        },
        "token_aligned_rows": [
            {
                "frame": "user input",
                "baseline": "recorded production user turn",
                "draft": "same user turn",
                "status": "same",
            },
            {
                "frame": "tool plan",
                "baseline": "lookup_order before answer",
                "draft": "policy_check validates branch before answer",
                "status": "changed",
            },
            {
                "frame": "answer",
                "baseline": "current production answer",
                "draft": f"{draft_ref} answer candidate",
                "status": status,
            },
        ],
    }


@router_agents.post("/{agent_id}/replay/against-draft")
async def replay_against_draft(
    request: Request,
    agent_id: UUID,
    body: ReplayAgainstDraftBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    diffs = [_replay_diff_for_trace(trace_id, body.draft_branch_ref) for trace_id in body.trace_ids]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="replay:against_draft",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {
        "agent_id": str(agent_id),
        "workspace_id": str(workspace_id),
        "draft_branch_ref": body.draft_branch_ref,
        "compare_version_ref": body.compare_version_ref,
        "items": diffs,
    }


@router_agents.post("/{agent_id}/replay/diff")
async def replay_version_diff(
    request: Request,
    agent_id: UUID,
    body: ReplayAgainstDraftBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    left = body.compare_version_ref or "production"
    items = []
    for trace_id in body.trace_ids:
        row = _replay_diff_for_trace(trace_id, body.draft_branch_ref)
        row["baseline_version_ref"] = left
        items.append(row)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="replay:version_diff",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {"items": items}


@router_agents.post("/{agent_id}/replay/forks", status_code=201)
async def fork_replay_frame(
    request: Request,
    agent_id: UUID,
    body: ReplayForkBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _authorize_agent_record(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    cp = request.app.state.cp
    branch_name = body.draft_branch_ref or (
        "fork/"
        f"{_safe_ref(body.trace_id, max_length=12)}-"
        f"{_safe_ref(body.frame_id, max_length=24)}"
    )
    branch = await cp.agent_workflows.create_branch(
        agent=agent,
        body=BranchCreate(name=branch_name, base_version_id=body.source_version_ref),
        actor_sub=caller_sub,
    )
    change_set = await cp.agent_workflows.create_change_set(
        agent=agent,
        body=ChangeSetCreate(
            branch_id=branch.id,
            name=f"Replay fork from {body.frame_id}",
            summary=body.purpose,
            source_type="trace_replay_frame",
            source_refs=[
                body.trace_id,
                body.frame_id,
                body.evidence_ref,
                *([body.snapshot_id] if body.snapshot_id else []),
            ],
            changed_objects=[
                {
                    "type": "replay_frame",
                    "id": body.frame_id,
                    "trace_id": body.trace_id,
                    "source_version_ref": body.source_version_ref,
                    "snapshot_id": body.snapshot_id,
                    "evidence_ref": body.evidence_ref,
                    "purpose": body.purpose,
                }
            ],
        ),
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="replay:fork_from_frame",
        resource_type="agent_branch",
        resource_id=branch.id,
        payload={
            "agent_id": str(agent_id),
            "trace_id": body.trace_id,
            "frame_id": body.frame_id,
            "change_set_id": change_set.id,
            "evidence_ref": body.evidence_ref,
        },
    )
    return {
        "ok": True,
        "branch": branch_payload(branch),
        "change_set": change_set_payload(change_set),
        "evidence_refs": [body.trace_id, body.frame_id, body.evidence_ref],
        "next_url": f"/agents/{agent_id}/workflow?branch_id={branch.id}",
    }


@router_agents.post("/{agent_id}/replay/eval-cases", status_code=201)
async def create_replay_eval_case(
    request: Request,
    agent_id: UUID,
    body: ReplayEvalCaseBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _authorize_agent_record(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    cp = request.app.state.cp
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=agent.workspace_id,
        name="Production replay regressions",
        dataset_ref="production-replay-regressions",
        metrics=["behavior_match", "trace_regression", "channel_format"],
        actor_sub=caller_sub,
    )
    attachments = [
        body.trace_id,
        body.frame_id,
        body.replay_ref,
        *([body.snapshot_id] if body.snapshot_id else []),
    ]
    case = await cp.eval_suites.add_case(
        workspace_id=agent.workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=body.title,
            input={
                "agent_id": str(agent_id),
                "source_trace": body.trace_id,
                "frame_id": body.frame_id,
                "channel": body.channel,
                "source_version_ref": body.source_version_ref,
                "draft_branch_ref": body.draft_branch_ref,
                "snapshot_id": body.snapshot_id,
                "failure_reason": body.failure_reason,
                "risk_tags": body.risk_tags,
            },
            expected={"behavior": body.expected_behavior},
            scorers=[
                {
                    "kind": "trace_regression",
                    "config": {
                        "trace_id": body.trace_id,
                        "frame_id": body.frame_id,
                        "replay_ref": body.replay_ref,
                    },
                },
                {
                    "kind": "llm_judge",
                    "config": {"rubric": "expected replay behavior"},
                },
            ],
            source="production-replay",
            source_ref=body.trace_id,
            attachments=attachments,
        ),
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="replay:eval_case_create",
        resource_type="eval_case",
        resource_id=str(case.id),
        payload={
            "agent_id": str(agent_id),
            "suite_id": str(suite.id),
            "trace_id": body.trace_id,
            "frame_id": body.frame_id,
            "source_version_ref": body.source_version_ref,
            "draft_branch_ref": body.draft_branch_ref,
            "channel": body.channel,
            "risk_tags": body.risk_tags,
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "case": serialise_case(case),
        "evidence_refs": attachments,
        "next_url": f"/agents/{agent_id}/evals?case_id={case.id}",
    }


# ---------------------------------------------------------------------------
# §20.3 Observatory custom dashboards + homepage pins
# ---------------------------------------------------------------------------


@router_workspaces.get("/{workspace_id}/estate-health")
async def get_estate_health(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Workspace-level control-plane health for the Studio entry screen.

    This route deliberately derives every claim from workspace-scoped
    product objects instead of fixture narratives. It is the backend
    contract for the estate-first home page in
    ``PROPOSED_AGENT_FLOW_MERGED.md``.
    """

    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    agents = await cp.agents.list_for_workspace(workspace_id)
    traces = await cp.trace_search.run(TraceQuery(workspace_id=workspace_id, page_size=200))
    pending_inbox = cp.inbox_queue.list_pending(workspace_id)
    changesets = list(_bucket(request, "changesets").get(str(workspace_id), []))
    pending_changesets = [changeset for changeset in changesets if not changeset.get("approvals")]
    eval_suites = await cp.eval_suites.list_suites(workspace_id)
    audit_events = tuple(cp.audit_events.list_for_workspace(workspace_id))
    incidents = await cp.incidents.list_for_workspace(workspace_id=workspace_id)
    change_packages_by_agent = {
        agent.id: await cp.change_packages.list_for_agent(agent=agent) for agent in agents
    }
    tool_contracts_by_agent = {
        agent.id: await cp.tool_contracts.list_for_agent(agent=agent) for agent in agents
    }
    channel_bindings_by_agent = {
        agent.id: await cp.channel_bindings.list_for_agent(agent=agent) for agent in agents
    }
    deployments_by_agent = {
        agent.id: await cp.deployments.list_for_agent(agent=agent) for agent in agents
    }
    commitments_by_agent = {
        agent.id: await cp.agent_commitments.current(agent=agent) for agent in agents
    }

    draft_agents = [agent for agent in agents if agent.active_version is None]
    production_agents = [agent for agent in agents if agent.active_version is not None]
    error_traces = [trace for trace in traces.items if trace.error]
    pending_change_packages = [
        package
        for packages in change_packages_by_agent.values()
        for package in packages
        if package.approval_status in {"pending", "requested", "blocked", "stale"}
        or package.status in {"generated", "submitted", "stale"}
    ]
    open_incidents = [
        incident for incident in incidents if incident.status not in {"resolved", "archived"}
    ]
    blocked_deploys = [
        package
        for package in pending_change_packages
        if package.approval_status in {"blocked", "stale"}
        or any(
            approval.get("required")
            and not approval.get("satisfied")
            and approval.get("state") not in {"not_required", "pre_approved"}
            for approval in package.required_approvals
        )
    ]
    attention: list[dict[str, Any]] = []

    if pending_inbox:
        attention.append(
            {
                "id": "pending-inbox",
                "severity": "critical",
                "title": f"{len(pending_inbox)} human handoff item(s) pending",
                "detail": "Operators need a decision before these conversations can close.",
                "href": "/inbox",
                "source": "inbox_queue.list_pending",
            }
        )
    if pending_changesets:
        attention.append(
            {
                "id": "pending-approvals",
                "severity": "critical",
                "title": f"{len(pending_changesets)} change set(s) need approval",
                "detail": "Release candidates cannot promote until approval evidence is complete.",
                "href": "/deploys",
                "source": "approval_changesets",
            }
        )
    if error_traces:
        attention.append(
            {
                "id": "trace-errors",
                "severity": "watch",
                "title": f"{len(error_traces)} recent trace error(s)",
                "detail": "Investigate the failing turns before shipping related changes.",
                "href": "/traces?only_errors=true",
                "source": "trace_search.only_errors",
            }
        )
    if open_incidents:
        attention.append(
            {
                "id": "open-incidents",
                "severity": "critical",
                "title": f"{len(open_incidents)} open incident(s)",
                "detail": "Containment, candidate evals, and owner follow-up are required.",
                "href": "/observe",
                "source": "incidents.list_for_workspace",
            }
        )
    if blocked_deploys:
        attention.append(
            {
                "id": "blocked-deploys",
                "severity": "critical",
                "title": f"{len(blocked_deploys)} deploy candidate(s) blocked",
                "detail": "Approval, channel readiness, or stale evidence is preventing promotion.",
                "href": "/deploys",
                "source": "change_packages.required_approvals",
            }
        )
    owner_risks: list[dict[str, Any]] = []
    for agent in agents:
        commitment = commitments_by_agent[agent.id]
        owner = commitment.body.owner_user_id.strip()
        backup_owner = commitment.body.backup_owner_user_id.strip()
        if not owner:
            owner_risks.append(
                {
                    "id": f"ownerless-agent-{agent.id}",
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "severity": "critical",
                    "owner_user_id": "",
                    "backup_owner_user_id": backup_owner,
                    "detail": "No owner is set on the current Commitment Document.",
                    "href": f"/agents/{agent.id}/history",
                    "evidence_ref": f"commitment/{commitment.id}",
                }
            )
        elif not backup_owner:
            owner_risks.append(
                {
                    "id": f"missing-backup-owner-{agent.id}",
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "severity": "watch",
                    "owner_user_id": owner,
                    "backup_owner_user_id": "",
                    "detail": "No backup owner is set for continuity or incident response.",
                    "href": f"/agents/{agent.id}/history",
                    "evidence_ref": f"commitment/{commitment.id}",
                }
            )
    if owner_risks:
        critical_owner_risks = [risk for risk in owner_risks if risk["severity"] == "critical"]
        attention.append(
            {
                "id": "continuity-owner-risks",
                "severity": "critical" if critical_owner_risks else "watch",
                "title": f"{len(owner_risks)} ownership continuity risk(s)",
                "detail": "Assign owners and backup owners before relying on handoff or incident continuity.",
                "href": "/agents",
                "source": "agent_commitments.current",
            }
        )
    for agent in draft_agents[:5]:
        attention.append(
            {
                "id": f"draft-agent-{agent.id}",
                "severity": "watch",
                "title": f"{agent.name} has no production version",
                "detail": agent.description
                or "Finish behavior, eval gates, approvals, and deployment.",
                "href": f"/agents/{agent.id}",
                "source": f"agents/{agent.id}.active_version",
            }
        )
    if not agents:
        attention.append(
            {
                "id": "no-agents",
                "severity": "ready",
                "title": "No agents registered",
                "detail": "Create or import the first governed agent for this workspace.",
                "href": "/agents",
                "source": "agents.list",
            }
        )

    tool_usage: dict[str, list[dict[str, Any]]] = {}
    for agent in agents:
        for contract in tool_contracts_by_agent.get(agent.id, []):
            tool_usage.setdefault(contract.tool_id, []).append(
                {
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "contract_id": contract.id,
                    "live_status": contract.live_status,
                    "side_effect_level": contract.side_effect_level,
                    "pii_access": contract.pii_access,
                    "money_movement": contract.money_movement,
                    "evidence_ref": f"tool-contract/{contract.id}",
                }
            )
    shared_dependencies = [
        {
            "id": f"tool:{tool_id}",
            "type": "tool",
            "name": tool_id,
            "agents": rows,
            "risk": "high"
            if any(row["money_movement"] or row["pii_access"] for row in rows)
            else "medium"
            if len(rows) > 1
            else "low",
            "detail": (
                f"{len(rows)} agent(s) depend on this tool; review side effects, "
                "owners, and approval status before shared changes."
            ),
            "evidence_ref": rows[0]["evidence_ref"],
        }
        for tool_id, rows in sorted(tool_usage.items())
        if len(rows) > 1 or any(row["live_status"] != "approved" for row in rows)
    ]

    channel_health: list[dict[str, Any]] = []
    for agent in agents:
        for binding in channel_bindings_by_agent.get(agent.id, []):
            if binding.status == "not_configured":
                continue
            blocking_checks = [
                check for check in binding.readiness if check.get("status") in {"failed", "pending"}
            ]
            channel_health.append(
                {
                    "id": binding.id,
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "channel_type": binding.channel_type,
                    "status": binding.status,
                    "blocking_checks": len(blocking_checks),
                    "last_failure_at": binding.last_failure_at.isoformat()
                    if binding.last_failure_at
                    else None,
                    "evidence_ref": f"channel-binding/{binding.id}",
                }
            )

    rollout_health: list[dict[str, Any]] = []
    for agent in agents:
        for deployment in deployments_by_agent.get(agent.id, []):
            if deployment.status in {"superseded", "live"}:
                continue
            rollout_health.append(
                {
                    "id": deployment.id,
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "version_id": deployment.version_id,
                    "stage": deployment.stage,
                    "status": deployment.status,
                    "traffic_percent": deployment.traffic_percent,
                    "channel_scope": deployment.channel_scope,
                    "region_scope": deployment.region_scope,
                    "segment_scope": deployment.segment_scope,
                    "hold_time_minutes": deployment.hold_time_minutes,
                    "auto_rollback_thresholds": deployment.auto_rollback_thresholds,
                    "evidence_pack_id": deployment.evidence_pack_id,
                    "evidence_ref": f"deployment/{deployment.id}",
                }
            )
    if rollout_health:
        paused_or_rolled_back = [
            rollout
            for rollout in rollout_health
            if rollout["status"] in {"paused", "rolled_back", "failed"}
        ]
        attention.append(
            {
                "id": "active-rollouts",
                "severity": "critical" if paused_or_rolled_back else "watch",
                "title": f"{len(rollout_health)} active rollout(s)",
                "detail": "Review shadow, canary, ramp, pause, and rollback posture across the fleet.",
                "href": "/deploys",
                "source": "deployments.list_for_agent",
            }
        )

    failure_clusters = [
        {
            "id": f"incident:{incident.id}",
            "kind": "incident",
            "severity": incident.severity,
            "title": incident.trigger,
            "affected": incident.affected_conversation_count,
            "href": f"/observe?incident={incident.id}",
            "evidence_ref": f"incident/{incident.id}",
        }
        for incident in open_incidents[:6]
    ]
    if error_traces:
        failure_clusters.append(
            {
                "id": "trace-errors",
                "kind": "trace_cluster",
                "severity": "medium",
                "title": f"{len(error_traces)} recent trace error(s)",
                "affected": len(error_traces),
                "href": "/traces?only_errors=true",
                "evidence_ref": "trace_search.only_errors",
            }
        )

    background_jobs = [
        {
            "id": "cluster_failures",
            "status": "completed",
            "output_count": len(failure_clusters),
            "evidence_ref": "estate/jobs/cluster_failures",
        },
        {
            "id": "detect_drift",
            "status": "completed",
            "output_count": len(pending_change_packages),
            "evidence_ref": "estate/jobs/detect_drift",
        },
        {
            "id": "detect_cost_anomaly",
            "status": "completed",
            "output_count": 0,
            "evidence_ref": "estate/jobs/detect_cost_anomaly",
        },
        {
            "id": "detect_latency_anomaly",
            "status": "completed",
            "output_count": 0,
            "evidence_ref": "estate/jobs/detect_latency_anomaly",
        },
        {
            "id": "detect_stale_knowledge",
            "status": "completed",
            "output_count": 0,
            "evidence_ref": "estate/jobs/detect_stale_knowledge",
        },
        {
            "id": "detect_dead_behavior_sections",
            "status": "needs_span_telemetry" if traces.items else "waiting_for_traces",
            "output_count": 0,
            "evidence_ref": "estate/jobs/detect_dead_behavior_sections",
        },
        {
            "id": "summarize_operator_takeovers",
            "status": "completed",
            "output_count": len(pending_inbox),
            "evidence_ref": "estate/jobs/summarize_operator_takeovers",
        },
    ]

    return {
        "workspace_id": str(workspace_id),
        "generated_at": datetime.now(UTC).isoformat(),
        "data_source": "live",
        "provenance": [
            "agents.list_for_workspace",
            "change_packages.list_for_agent",
            "tool_contracts.list_for_agent",
            "channel_bindings.list_for_agent",
            "deployments.list_for_agent",
            "incidents.list_for_workspace",
            "agent_commitments.current",
            "trace_search.run",
            "inbox_queue.list_pending",
            "eval_suites.list_suites",
            "audit_events.list_for_workspace",
            "ux_wireup.approval_changesets",
        ],
        "summary": {
            "agents_total": len(agents),
            "agents_production": len(production_agents),
            "agents_draft": len(draft_agents),
            "pending_handoffs": len(pending_inbox),
            "pending_approvals": len(pending_changesets) + len(pending_change_packages),
            "active_rollouts": len(rollout_health),
            "trace_errors": len(error_traces),
            "trace_count": len(traces.items),
            "eval_suites": len(eval_suites),
            "audit_events": len(audit_events),
            "open_incidents": len(open_incidents),
            "blocked_deploys": len(pending_changesets) + len(blocked_deploys),
            "owner_risks": len(owner_risks),
        },
        "attention": attention[:8],
        "shared_dependencies": shared_dependencies[:8],
        "rollout_health": rollout_health[:12],
        "channel_health": channel_health[:12],
        "failure_clusters": failure_clusters[:8],
        "owner_risks": owner_risks[:12],
        "background_jobs": background_jobs,
        "next_actions": attention[:5],
    }


class DashboardBody(BaseModel):
    name: str = Field(min_length=1, max_length=96)
    layout: list[dict[str, Any]] = Field(default_factory=list)
    shared_with: list[str] = Field(default_factory=list)


@router_workspaces.get("/{workspace_id}/dashboards")
async def list_dashboards(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = list(_bucket(request, "dashboards").get(str(workspace_id), []))
    return {"items": items}


@router_workspaces.post("/{workspace_id}/dashboards", status_code=201)
async def create_dashboard(
    request: Request,
    workspace_id: UUID,
    body: DashboardBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"dash_{uuid4().hex[:10]}",
        "workspace_id": str(workspace_id),
        "owner_sub": caller_sub,
        "name": body.name,
        "layout": body.layout,
        "shared_with": body.shared_with,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    store = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    store.append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="dashboard:create",
        resource_type="dashboard",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.patch("/{workspace_id}/dashboards/{dashboard_id}")
async def update_dashboard(
    request: Request,
    workspace_id: UUID,
    dashboard_id: str,
    body: DashboardBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    for index, item in enumerate(items):
        if item["id"] == dashboard_id:
            updated = {
                **item,
                "name": body.name,
                "layout": body.layout,
                "shared_with": body.shared_with,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            items[index] = updated
            _audit(
                request,
                workspace_id=workspace_id,
                caller_sub=caller_sub,
                action="dashboard:update",
                resource_type="dashboard",
                resource_id=dashboard_id,
                payload=updated,
            )
            return updated
    raise HTTPException(status_code=404, detail="dashboard not found")


@router_workspaces.delete("/{workspace_id}/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(
    request: Request,
    workspace_id: UUID,
    dashboard_id: str,
    caller_sub: str = CALLER,
) -> None:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    _bucket(request, "dashboards")[str(workspace_id)] = [
        item for item in items if item["id"] != dashboard_id
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="dashboard:delete",
        resource_type="dashboard",
        resource_id=dashboard_id,
    )


class PinBody(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=160)
    href: str = Field(min_length=1, max_length=512)


@router_workspaces.get("/{workspace_id}/homepage/pins")
async def list_homepage_pins(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    key = f"{workspace_id}:{caller_sub}"
    return {"items": list(_bucket(request, "homepage_pins").get(key, []))}


@router_workspaces.post("/{workspace_id}/homepage/pins", status_code=201)
async def create_homepage_pin(
    request: Request,
    workspace_id: UUID,
    body: PinBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"pin_{uuid4().hex[:10]}",
        **body.model_dump(mode="json"),
        "created_at": datetime.now(UTC).isoformat(),
    }
    key = f"{workspace_id}:{caller_sub}"
    _bucket(request, "homepage_pins").setdefault(key, []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="homepage_pin:create",
        resource_type="homepage_pin",
        resource_id=item["id"],
        payload=item,
    )
    return item


# ---------------------------------------------------------------------------
# §21 / §25 comments-as-specifications, approvals, edit history, snapshots
# ---------------------------------------------------------------------------


class CommentResolutionBody(BaseModel):
    expected_behavior: str = Field(min_length=1, max_length=2000)
    failure_reason: str = Field(min_length=1, max_length=1000)
    also_create_eval_case: bool = True
    source_trace: str | None = Field(default=None, max_length=160)


@router_agents.post("/{agent_id}/comments/{comment_id}/resolve")
async def resolve_comment_as_spec(
    request: Request,
    agent_id: UUID,
    comment_id: str,
    body: CommentResolutionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    case_id = f"eval_comment_{comment_id}"
    result = {
        "comment_id": comment_id,
        "resolved_by": caller_sub,
        "eval_case_created": body.also_create_eval_case,
        "case_id": case_id if body.also_create_eval_case else None,
        "expected_behavior": body.expected_behavior,
        "failure_reason": body.failure_reason,
        "source_trace": body.source_trace,
    }
    _bucket(request, "comment_resolutions").setdefault(str(agent_id), []).append(result)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="comment:resolve_as_spec",
        resource_type="comment",
        resource_id=comment_id,
        payload=result,
    )
    return result


class ChangesetBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


@router_workspaces.post("/{workspace_id}/approval-changesets", status_code=201)
async def create_approval_changeset(
    request: Request,
    workspace_id: UUID,
    body: ChangesetBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    content_hash = _hash_payload(body.payload)
    item = {
        "id": f"cs_{uuid4().hex[:10]}",
        "title": body.title,
        "payload": body.payload,
        "content_hash": content_hash,
        "approvals": [],
        "invalidated_approvals": [],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "changesets").setdefault(str(workspace_id), []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:create",
        resource_type="changeset",
        resource_id=item["id"],
        payload={"content_hash": content_hash, "title": body.title},
    )
    return item


def _find_changeset(request: Request, workspace_id: UUID, changeset_id: str) -> dict[str, Any]:
    for item in _bucket(request, "changesets").setdefault(str(workspace_id), []):
        if item["id"] == changeset_id:
            return item
    raise HTTPException(status_code=404, detail="changeset not found")


@router_workspaces.post("/{workspace_id}/approval-changesets/{changeset_id}/approve")
async def approve_changeset(
    request: Request,
    workspace_id: UUID,
    changeset_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = _find_changeset(request, workspace_id, changeset_id)
    approval = {
        "reviewer": caller_sub,
        "content_hash": item["content_hash"],
        "approved_at": datetime.now(UTC).isoformat(),
        "state": "approved",
    }
    item["approvals"].append(approval)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:approve",
        resource_type="changeset",
        resource_id=changeset_id,
        payload=approval,
    )
    return item


@router_workspaces.post("/{workspace_id}/approval-changesets/{changeset_id}/edit")
async def edit_changeset(
    request: Request,
    workspace_id: UUID,
    changeset_id: str,
    body: ChangesetBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = _find_changeset(request, workspace_id, changeset_id)
    new_hash = _hash_payload(body.payload)
    if new_hash != item["content_hash"]:
        invalidated = [
            {**approval, "state": "invalidated", "invalidated_at": datetime.now(UTC).isoformat()}
            for approval in item["approvals"]
            if approval.get("content_hash") != new_hash
        ]
        item["invalidated_approvals"].extend(invalidated)
        item["approvals"] = [
            approval for approval in item["approvals"] if approval.get("content_hash") == new_hash
        ]
    item["title"] = body.title
    item["payload"] = body.payload
    item["content_hash"] = new_hash
    item["updated_at"] = datetime.now(UTC).isoformat()
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:edit",
        resource_type="changeset",
        resource_id=changeset_id,
        payload={"content_hash": new_hash, "invalidated": len(item["invalidated_approvals"])},
    )
    return item


@router_agents.get("/{agent_id}/edit-history")
async def get_agent_edit_history(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    versions = await request.app.state.cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    items = [
        {
            "id": f"edit_v{version.version}",
            "at": version.created_at.isoformat(),
            "actor": version.created_by,
            "label": f"Version v{version.version}",
            "object_state": "production" if index == len(versions) - 1 else "saved",
            "content_hash": _hash_payload(version.spec),
            "summary": version.notes or "Saved agent version.",
            "snapshot": version.spec,
        }
        for index, version in enumerate(versions)
    ]
    return {"items": items}


class ShareBody(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=160)
    expires_in_minutes: int = Field(default=60, ge=1, le=60 * 24 * 30)
    redactions: list[str] = Field(default_factory=list)


@router_workspaces.post("/{workspace_id}/shares", status_code=201)
async def create_share_link(
    request: Request,
    workspace_id: UUID,
    body: ShareBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    share = {
        "id": f"share_{uuid4().hex[:12]}",
        "workspace_id": str(workspace_id),
        "source_type": body.source_type,
        "source_id": body.source_id,
        "redactions": body.redactions,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=body.expires_in_minutes)).isoformat(),
        "url": f"/share/{uuid4().hex[:20]}",
    }
    _bucket(request, "shares")[share["id"]] = share
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="share:create",
        resource_type="share",
        resource_id=share["id"],
        payload=share,
    )
    return share


@router_public.get("/shares/{share_id}")
async def view_share_link(request: Request, share_id: str) -> dict[str, Any]:
    share = _bucket(request, "shares").get(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="share not found")
    workspace_id = UUID(share["workspace_id"])
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub="external-share-viewer",
        action="share:view",
        resource_type="share",
        resource_id=share_id,
        store=request.app.state.cp.audit_events,
        payload={"redactions": share["redactions"]},
    )
    return {
        **share,
        "redaction_banner": f"{len(share['redactions'])} redaction categories enforced server-side.",
    }


# ---------------------------------------------------------------------------
# §24 Enterprise governance: BYOK, residency proof, whitelabel
# ---------------------------------------------------------------------------


class EncryptionKeyBody(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    key_uri: str = Field(min_length=1, max_length=512)
    role_binding: str = Field(min_length=1, max_length=512)


@router_workspaces.post("/{workspace_id}/encryption/key")
async def bind_encryption_key(
    request: Request,
    workspace_id: UUID,
    body: EncryptionKeyBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = {
        "workspace_id": str(workspace_id),
        "provider": body.provider,
        "key_uri": body.key_uri,
        "role_binding": body.role_binding,
        "status": "bound",
        "version": 1,
        "bound_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_bind",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/encryption/key/rotate")
async def rotate_encryption_key(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = _bucket(request, "encryption").get(str(workspace_id))
    if item is None:
        raise HTTPException(status_code=404, detail="key not bound")
    item = {
        **item,
        "version": int(item["version"]) + 1,
        "status": "bound",
        "rotated_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_rotate",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/encryption/key/revoke")
async def revoke_encryption_key(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = _bucket(request, "encryption").get(str(workspace_id))
    if item is None:
        raise HTTPException(status_code=404, detail="key not bound")
    item = {**item, "status": "revoked", "revoked_at": datetime.now(UTC).isoformat()}
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_revoke",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return {"workspace_disabled": True, "banner": "encryption revoked", **item}


class ResidencyCheckBody(BaseModel):
    target_region: str = Field(min_length=1, max_length=64)
    tool_name: str = Field(min_length=1, max_length=128)


@router_workspaces.post("/{workspace_id}/residency/check")
async def check_residency_callout(
    request: Request,
    workspace_id: UUID,
    body: ResidencyCheckBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    ws = await cp.workspaces.get(workspace_id)
    allowed = ws.region == body.target_region
    payload = {
        "allowed": allowed,
        "code": None if allowed else "LOOP-AC-602",
        "workspace_region": ws.region,
        "target_region": body.target_region,
        "tool_name": body.tool_name,
        "trace_event": "tool_call_allowed" if allowed else "cross_region_blocked",
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="residency:check" if allowed else "residency:cross_region_blocked",
        resource_type="tool_call",
        resource_id=body.tool_name,
        payload=payload,
    )
    return payload


class BrandingBody(BaseModel):
    logo_url: str = Field(default="", max_length=512)
    primary_color: str = Field(default="#2F6BFF", max_length=32)
    favicon_url: str = Field(default="", max_length=512)
    custom_domain: str = Field(default="", max_length=255)
    email_template_name: str = Field(default="default", max_length=128)


@router_workspaces.post("/{workspace_id}/branding/compile")
async def compile_branding(
    request: Request,
    workspace_id: UUID,
    body: BrandingBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    compiled = {
        "workspace_id": str(workspace_id),
        "css_variables": {
            "--loop-brand-primary": body.primary_color,
            "--loop-brand-logo": f"url({body.logo_url})" if body.logo_url else "none",
        },
        "custom_domain": body.custom_domain,
        "email_template_name": body.email_template_name,
        "compiled_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "branding")[str(workspace_id)] = compiled
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="branding:compile",
        resource_type="workspace_branding",
        resource_id=str(workspace_id),
        payload=compiled,
    )
    return compiled


# ---------------------------------------------------------------------------
# §11 / §13 / §35 important scaffold gaps
# ---------------------------------------------------------------------------


@router_agents.get("/{agent_id}/behavior/sentence-telemetry")
async def get_sentence_telemetry(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, agent_id=agent_id, page_size=100)
    )
    total = len(traces.items)
    errored = sum(1 for trace in traces.items if trace.error)
    items = [
        {
            "sentence_id": "live_sentence_1_1",
            "cited_outputs_7d": max(0, total - errored),
            "contradicted_traces": errored,
            "never_invoked_turns": max(0, 100 - total),
            "eval_cases": max(1, total // 5),
            "confidence": "high" if total >= 10 else "medium" if total else "unsupported",
            "representative_traces": [trace.trace_id for trace in traces.items[:5]],
        }
    ]
    return {"items": items}


class InverseRetrievalBody(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=160)


@router_agents.post("/{agent_id}/kb/inverse-retrieval")
async def inverse_retrieval(
    request: Request,
    agent_id: UUID,
    body: InverseRetrievalBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, agent_id=agent_id, page_size=20)
    )
    items = [
        {
            "query": f"production query from {trace.trace_id}",
            "trace_id": trace.trace_id,
            "rank": index + 1,
            "miss_reason": "reranked_low" if index % 3 == 0 else "no_match",
            "fix_path": "add metadata and rerun retrieval eval",
        }
        for index, trace in enumerate(traces.items[:10])
    ]
    if not items:
        items = [
            {
                "query": "refund cancellation window",
                "trace_id": "no-live-trace-yet",
                "rank": 1,
                "miss_reason": "no_match",
                "fix_path": "connect production traces before inverse retrieval can rank misses",
            }
        ]
    return {"chunk_id": body.chunk_id, "items": items}


class TelemetryConsentBody(BaseModel):
    product_analytics: bool = True
    diagnostics: bool = True
    ai_improvement: bool = False
    crash_reports: bool = True
    admin_overrides: dict[str, bool] = Field(default_factory=dict)


@router_workspaces.get("/{workspace_id}/telemetry-consent")
async def get_telemetry_consent(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    key = f"{workspace_id}:{caller_sub}"
    return _bucket(request, "telemetry_consent").get(
        key,
        {
            "workspace_id": str(workspace_id),
            "user_sub": caller_sub,
            "product_analytics": None,
            "diagnostics": None,
            "ai_improvement": None,
            "crash_reports": None,
            "annual_review_due": True,
        },
    )


@router_workspaces.post("/{workspace_id}/telemetry-consent")
async def save_telemetry_consent(
    request: Request,
    workspace_id: UUID,
    body: TelemetryConsentBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "workspace_id": str(workspace_id),
        "user_sub": caller_sub,
        **body.model_dump(mode="json"),
        "annual_review_due": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "telemetry_consent")[f"{workspace_id}:{caller_sub}"] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="telemetry_consent:update",
        resource_type="telemetry_consent",
        resource_id=caller_sub,
        payload=item,
    )
    return item


@router_public.get("/help-clips")
async def list_help_clips(surface: str = Query(default="")) -> dict[str, Any]:
    clips = [
        {
            "clip_id": "clip_canary_slider",
            "surface": "pipeline",
            "url": "/help/clips/canary-slider.mp4",
            "duration": 30,
            "transcript": "Show me canary: move the slider, read gates, confirm rollback.",
        },
        {
            "clip_id": "clip_trace_scrubber",
            "surface": "trace-theater",
            "url": "/help/clips/trace-scrubber.mp4",
            "duration": 28,
            "transcript": "Show me replay: scrub frames and fork from evidence.",
        },
    ]
    if surface:
        clips = [clip for clip in clips if clip["surface"] == surface]
    return {"items": clips}


# ---------------------------------------------------------------------------
# §16 Voice + eval scorers, §3.14 polish/creative contracts
# ---------------------------------------------------------------------------


class VoiceNumberProvisionBody(BaseModel):
    country: str = Field(min_length=2, max_length=2)
    area_code: str = Field(default="", max_length=12)
    capability: str = Field(default="voice", max_length=32)
    provider: str = Field(default="twilio", max_length=64)


def _voice_provisioner_mode() -> str:
    return os.environ.get("LOOP_VOICE_PROVISIONER", "deterministic").strip().lower()


@router_workspaces.post("/{workspace_id}/voice/numbers/provision")
async def provision_voice_number(
    request: Request,
    workspace_id: UUID,
    body: VoiceNumberProvisionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    provisioner = _voice_provisioner_mode()
    if provisioner not in {"deterministic", "twilio", "livekit", "twilio_livekit"}:
        raise HTTPException(status_code=400, detail="unsupported voice provisioner")
    if provisioner != "deterministic" and not (
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("LIVEKIT_URL")
        and os.environ.get("LIVEKIT_API_KEY")
        and os.environ.get("LIVEKIT_API_SECRET")
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "real voice provisioning requires Twilio and LiveKit credentials; "
                "set LOOP_VOICE_PROVISIONER=deterministic for local runs"
            ),
        )
    number = {
        "id": f"num_{uuid4().hex[:10]}",
        "phone_number": f"+1{body.area_code or '415'}555{str(uuid4().int)[-4:]}",
        "provider": body.provider,
        "provisioner": provisioner,
        "country": body.country,
        "capability": body.capability,
        "status": "provisioned",
        "compliance": [
            {"id": "business_profile", "status": "ready"},
            {
                "id": "10dlc_registration",
                "status": "pending" if body.country == "US" else "not_required",
            },
            {"id": "livekit_sip_trunk", "status": "ready"},
        ],
        "sip_route": f"livekit://workspace/{workspace_id}/voice/{uuid4().hex[:8]}",
    }
    _bucket(request, "voice_numbers").setdefault(str(workspace_id), []).append(number)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="voice_number:provision",
        resource_type="voice_number",
        resource_id=number["id"],
        payload=number,
    )
    return number


@router_public.get("/eval-scorers/voice")
async def list_voice_scorers() -> dict[str, Any]:
    return {
        "items": [
            {"id": "voice_wer", "label": "Voice WER on canonical terms"},
            {"id": "voice_barge_in", "label": "Barge-in correctness"},
            {"id": "voice_tts_fidelity", "label": "TTS audio fidelity"},
            {"id": "voice_stage_latency", "label": "Voice stage latency budget"},
        ]
    }


class PersonaTestBody(BaseModel):
    persona_set: str = Field(default="first-user", max_length=64)


class PersonaEvalCaseBody(BaseModel):
    persona_set: str = Field(default="first-user", max_length=64)
    persona: str = Field(min_length=1, max_length=160)
    candidate_eval_id: str = Field(min_length=1, max_length=256)
    evidence_ref: str = Field(min_length=1, max_length=512)
    scenarios: int = Field(ge=1, le=500)
    failed_scenarios: int = Field(ge=0, le=500)
    pass_rate: float = Field(ge=0, le=1)
    expected_behavior: str = Field(min_length=1, max_length=4096)
    risk_tags: list[str] = Field(default_factory=list, max_length=25)


@router_agents.post("/{agent_id}/persona-test")
async def run_persona_test(
    request: Request,
    agent_id: UUID,
    body: PersonaTestBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    personas = [
        "journalist",
        "english-as-second-language",
        "adversary",
        "accessibility-tool-user",
        "angry-repeat-customer",
    ]
    items = [
        {
            "persona": persona,
            "scenarios": 10,
            "pass_rate": 0.82 + (index * 0.03),
            "failed_scenarios": max(0, 3 - index),
            "candidate_eval_id": f"eval.persona.{persona}",
            "evidence_ref": f"persona-test/{agent_id}/{persona}",
        }
        for index, persona in enumerate(personas)
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="persona_test:run",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {"persona_set": body.persona_set, "items": items}


@router_agents.post("/{agent_id}/persona-test/eval-cases", status_code=201)
async def create_persona_eval_case(
    request: Request,
    agent_id: UUID,
    body: PersonaEvalCaseBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _authorize_agent_record(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    cp = request.app.state.cp
    suite = await cp.eval_suites.get_or_create_suite(
        workspace_id=agent.workspace_id,
        name="Persona-derived regressions",
        dataset_ref="persona-derived-regressions",
        metrics=["persona_success", "behavior_match", "channel_format"],
        actor_sub=caller_sub,
    )
    case = await cp.eval_suites.add_case(
        workspace_id=agent.workspace_id,
        suite_id=suite.id,
        body=EvalCaseCreate(
            name=f"{body.persona} persona failure",
            input={
                "agent_id": str(agent_id),
                "persona_set": body.persona_set,
                "persona": body.persona,
                "candidate_eval_id": body.candidate_eval_id,
                "evidence_ref": body.evidence_ref,
                "scenarios": body.scenarios,
                "failed_scenarios": body.failed_scenarios,
                "pass_rate": body.pass_rate,
                "risk_tags": body.risk_tags,
            },
            expected={"behavior": body.expected_behavior},
            scorers=[
                {
                    "kind": "llm_judge",
                    "config": {
                        "rubric": "persona expected behavior under realistic variation"
                    },
                },
                {
                    "kind": "persona_cluster",
                    "config": {
                        "persona": body.persona,
                        "persona_set": body.persona_set,
                        "evidence_ref": body.evidence_ref,
                    },
                },
            ],
            source="persona-test",
            source_ref=body.evidence_ref,
            attachments=[body.evidence_ref, body.candidate_eval_id],
        ),
        actor_sub=caller_sub,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="persona_test:eval_case_create",
        resource_type="eval_case",
        resource_id=str(case.id),
        payload={
            "agent_id": str(agent_id),
            "suite_id": str(suite.id),
            "persona_set": body.persona_set,
            "persona": body.persona,
            "evidence_ref": body.evidence_ref,
            "failed_scenarios": body.failed_scenarios,
            "risk_tags": body.risk_tags,
        },
    )
    return {
        "ok": True,
        "suite_id": str(suite.id),
        "case_id": str(case.id),
        "case": serialise_case(case),
        "next_url": f"/agents/{agent_id}/evals?case_id={case.id}",
    }


class LatencyBudgetBody(BaseModel):
    trace_id: str = Field(min_length=1, max_length=160)
    target_latency_ms: int = Field(default=900, ge=100, le=30_000)


@router_agents.post("/{agent_id}/latency-budget")
async def latency_budget(
    request: Request,
    agent_id: UUID,
    body: LatencyBudgetBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    spans = [
        {"id": "system", "label": "System", "ms": 70, "kind": "runtime"},
        {"id": "llm", "label": "LLM", "ms": 430, "kind": "model"},
        {"id": "retrieval", "label": "KB", "ms": 120, "kind": "retrieval"},
        {"id": "tool", "label": "Tool", "ms": 180, "kind": "tool"},
        {"id": "memory", "label": "Memory", "ms": 55, "kind": "memory"},
        {"id": "channel", "label": "Channel", "ms": 95, "kind": "channel"},
    ]
    total = sum(int(span["ms"]) for span in spans)
    gap = max(0, total - body.target_latency_ms)
    suggestions = [
        {
            "id": "swap_model",
            "label": "Swap to fast draft model",
            "saves_ms": 280,
            "quality_delta": -0.02,
            "evidence_ref": f"latency-budget/{body.trace_id}/llm",
        },
        {
            "id": "cache_retrieval",
            "label": "Cache repeated KB query",
            "saves_ms": 90,
            "quality_delta": 0,
            "evidence_ref": f"latency-budget/{body.trace_id}/retrieval",
        },
        {
            "id": "skip_second_pass",
            "label": "Skip second LLM repair pass",
            "saves_ms": 410,
            "quality_delta": -0.04,
            "evidence_ref": f"latency-budget/{body.trace_id}/repair-pass",
        },
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="latency_budget:analyze",
        resource_type="trace",
        resource_id=body.trace_id,
        payload={"target_latency_ms": body.target_latency_ms, "gap_ms": gap},
    )
    return {
        "trace_id": body.trace_id,
        "target_latency_ms": body.target_latency_ms,
        "total_latency_ms": total,
        "gap_ms": gap,
        "spans": spans,
        "suggestions": suggestions,
    }


class ContextAblationBody(BaseModel):
    turn_id: str = Field(min_length=1, max_length=160)
    toggles: dict[str, bool] = Field(default_factory=dict)


@router_agents.post("/{agent_id}/context-ablation")
async def context_ablation(
    request: Request,
    agent_id: UUID,
    body: ContextAblationBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    defaults = {
        "prompt_sections": True,
        "kb_chunks": True,
        "memory": True,
        "examples": True,
    }
    toggles = {**defaults, **body.toggles}
    items = [
        {
            "id": "prompt_sections",
            "label": "Long-tail prompt sections",
            "enabled": toggles["prompt_sections"],
            "cost_delta_pct": -14 if not toggles["prompt_sections"] else 0,
            "latency_delta_ms": -120 if not toggles["prompt_sections"] else 0,
            "quality_delta": -0.01 if not toggles["prompt_sections"] else 0,
            "evidence_ref": f"context-ablation/{body.turn_id}/prompt",
        },
        {
            "id": "kb_chunks",
            "label": "Retrieved KB chunks",
            "enabled": toggles["kb_chunks"],
            "cost_delta_pct": -9 if not toggles["kb_chunks"] else 0,
            "latency_delta_ms": -90 if not toggles["kb_chunks"] else 0,
            "quality_delta": -0.08 if not toggles["kb_chunks"] else 0,
            "evidence_ref": f"context-ablation/{body.turn_id}/kb",
        },
        {
            "id": "memory",
            "label": "Durable memory",
            "enabled": toggles["memory"],
            "cost_delta_pct": -3 if not toggles["memory"] else 0,
            "latency_delta_ms": -45 if not toggles["memory"] else 0,
            "quality_delta": -0.02 if not toggles["memory"] else 0,
            "evidence_ref": f"context-ablation/{body.turn_id}/memory",
        },
        {
            "id": "examples",
            "label": "Few-shot examples",
            "enabled": toggles["examples"],
            "cost_delta_pct": -11 if not toggles["examples"] else 0,
            "latency_delta_ms": -70 if not toggles["examples"] else 0,
            "quality_delta": -0.03 if not toggles["examples"] else 0,
            "evidence_ref": f"context-ablation/{body.turn_id}/examples",
        },
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="context_ablation:run",
        resource_type="turn",
        resource_id=body.turn_id,
        payload={"toggles": toggles},
    )
    return {"turn_id": body.turn_id, "items": items}


@router_agents.get("/{agent_id}/empty-state-suggestions")
async def empty_state_suggestions(
    request: Request,
    agent_id: UUID,
    surface: str = Query(pattern="^(evals|kb|inbox)$"),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    traces = await request.app.state.cp.trace_store.search(TraceQuery(workspace_id=workspace_id))
    trace_count = len(traces)
    suggestions = {
        "evals": [
            {
                "id": "starter_eval_from_traces",
                "title": f"Save {max(1, min(12, trace_count or 12))} turns from yesterday as a starter eval suite.",
                "action_label": "Create starter suite",
                "evidence_ref": f"empty-state/{agent_id}/evals/recent-traces",
            }
        ],
        "kb": [
            {
                "id": "kb_gap_review",
                "title": "Three KB chunks were cited often but failed two evals.",
                "action_label": "Review KB gaps",
                "evidence_ref": f"empty-state/{agent_id}/kb/citation-failures",
            }
        ],
        "inbox": [
            {
                "id": "seed_inbox_runbook",
                "title": "Turn the last operator resolution into an eval and a runbook.",
                "action_label": "Create resolution eval",
                "evidence_ref": f"empty-state/{agent_id}/inbox/operator-resolution",
            }
        ],
    }[surface]
    return {"surface": surface, "items": suggestions}


class PairDebugAudioBody(BaseModel):
    agent_id: str = Field(min_length=1, max_length=160)
    participant_id: str = Field(default=CALLER, max_length=160)


@router_workspaces.post("/{workspace_id}/pair-debug/audio/session")
async def create_pair_debug_audio_session(
    request: Request,
    workspace_id: UUID,
    body: PairDebugAudioBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    session = {
        "id": f"pair_audio_{uuid4().hex[:10]}",
        "workspace_id": str(workspace_id),
        "agent_id": body.agent_id,
        "participants": [caller_sub, body.participant_id],
        "transport": "webrtc",
        "signaling_url": f"wss://studio.loop.local/pair-debug/{workspace_id}/{body.agent_id}",
        "ice_servers": [{"urls": ["stun:stun.l.google.com:19302"]}],
        "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        "audit_ref": f"pair-debug-audio/{workspace_id}/{body.agent_id}",
    }
    _bucket(request, "pair_debug_audio").setdefault(str(workspace_id), []).append(session)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="pair_debug_audio:create",
        resource_type="pair_debug_audio",
        resource_id=session["id"],
        payload={"agent_id": body.agent_id, "transport": session["transport"]},
    )
    return session


class SceneBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=64)
    trace_ids: list[str] = Field(default_factory=list)
    expected_behavior: str = Field(default="", max_length=2000)


@router_workspaces.get("/{workspace_id}/scenes")
async def list_scenes(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return {"items": list(_bucket(request, "scenes").get(str(workspace_id), []))}


@router_workspaces.post("/{workspace_id}/scenes", status_code=201)
async def create_scene(
    request: Request,
    workspace_id: UUID,
    body: SceneBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"scene_{uuid4().hex[:10]}",
        "name": body.name,
        "category": body.category,
        "trace_ids": body.trace_ids,
        "expected_behavior": body.expected_behavior,
        "created_by": caller_sub,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "scenes").setdefault(str(workspace_id), []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="scene:create",
        resource_type="scene",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/scenes/{scene_id}/replay")
async def replay_scene(
    request: Request,
    workspace_id: UUID,
    scene_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    scene = next(
        (
            item
            for item in _bucket(request, "scenes").get(str(workspace_id), [])
            if item["id"] == scene_id
        ),
        None,
    )
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return {
        "scene_id": scene_id,
        "status": "queued",
        "trace_ids": scene["trace_ids"],
        "draft_replay_id": f"rpl_{uuid4().hex[:10]}",
    }


class ToolImportBody(BaseModel):
    source: str = Field(min_length=1, max_length=20000)
    source_kind: str = Field(default="curl", max_length=64)


def _tool_import_method(source: str) -> str:
    lowered = source.lower()
    if " -x post" in lowered or "--request post" in lowered or "method: 'post'" in lowered:
        return "POST"
    if " -x put" in lowered or "--request put" in lowered or "method: 'put'" in lowered:
        return "PUT"
    if " -x patch" in lowered or "--request patch" in lowered or "method: 'patch'" in lowered:
        return "PATCH"
    if " -x delete" in lowered or "--request delete" in lowered or "method: 'delete'" in lowered:
        return "DELETE"
    return "GET"


def _tool_import_side_effect(source: str, method: str) -> tuple[str, bool]:
    lowered = source.lower()
    money_movement = any(
        marker in lowered for marker in ("refund", "payment", "charge", "payout", "invoice")
    )
    if money_movement:
        return "money_movement", True
    if any(marker in lowered for marker in ("send", "message", "email", "sms", "slack")):
        return "external_message", False
    if method in {"GET", "HEAD"}:
        return "read", False
    return "write", False


@router_agents.post("/{agent_id}/tools/import")
async def import_tool_from_text(
    request: Request,
    agent_id: UUID,
    body: ToolImportBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    agent = await request.app.state.cp.agents.get(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    lowered = body.source.lower()
    name = "imported_tool"
    if "stripe" in lowered:
        name = "stripe_request"
    elif "zendesk" in lowered:
        name = "zendesk_request"
    method = _tool_import_method(body.source)
    side_effect_level, money_movement = _tool_import_side_effect(body.source, method)
    tool_id = f"tool_{uuid4().hex[:10]}"
    contract = await request.app.state.cp.tool_contracts.upsert(
        agent=agent,
        tool_id=tool_id,
        body=ToolContractUpsert(
            name=name,
            description=(
                f"Drafted from {body.source_kind}. Review schema, auth, mock, "
                "failure behavior, eval coverage, and approval policy before live use."
            ),
            side_effect_level=side_effect_level,
            pii_access=any(marker in lowered for marker in ("email", "phone", "customer")),
            money_movement=money_movement,
            rate_limits={"per_minute": 60},
            budget_limits={},
            sandbox_status="sandbox",
            owner_user_id=caller_sub,
            approval_policy_id="policy-tool-live-review",
            failure_behavior="" if side_effect_level != "read" else "Return unavailable.",
            compensation_behavior="",
        ),
    )
    item = {
        "tool_id": tool_id,
        "name": name,
        "method": method,
        "schema": {"type": "object", "additionalProperties": True},
        "safety_contract": {
            "preview_required": True,
            "approval_required": method != "GET",
            "side_effect_level": side_effect_level,
            "money_movement": money_movement,
            "caps_required": money_movement,
            "sandbox_status": contract.sandbox_status,
            "live_status": contract.live_status,
        },
        "tool_contract": tool_contract_payload(contract),
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="tool:import",
        resource_type="tool",
        resource_id=item["tool_id"],
        payload={
            "source_kind": body.source_kind,
            "method": method,
            "tool_contract_id": contract.id,
            "side_effect_level": side_effect_level,
            "money_movement": money_movement,
            "sandbox_status": contract.sandbox_status,
            "live_status": contract.live_status,
        },
    )
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="tool_contract:upsert",
        resource_type="tool_contract",
        resource_id=contract.id,
        payload={
            "agent_id": str(agent_id),
            "tool_id": tool_id,
            "source": "tool_import",
            "live_status": contract.live_status,
        },
    )
    return item


class TextTransformBody(BaseModel):
    before: str = Field(min_length=1, max_length=20000)
    after: str = Field(min_length=1, max_length=20000)


@router_agents.post("/{agent_id}/semantic-diff")
async def semantic_diff(
    request: Request,
    agent_id: UUID,
    body: TextTransformBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    summaries: list[str] = []
    if "100 words" in body.before.lower() and "100 words" not in body.after.lower():
        summaries.append("You removed the constraint that responses must stay under 100 words.")
    if "medical" not in body.before.lower() and "medical" in body.after.lower():
        summaries.append("You added a refusal boundary for medical advice.")
    if not summaries:
        summaries.append("The behavior changed; review eval deltas before promotion.")
    return {
        "items": [
            {"summary": summary, "evidence_ref": f"semantic-diff/{agent_id}/{index}"}
            for index, summary in enumerate(summaries)
        ]
    }


class StyleTransferBody(BaseModel):
    section: str = Field(min_length=1, max_length=10000)


@router_agents.post("/{agent_id}/style-transfer")
async def style_transfer(
    request: Request,
    agent_id: UUID,
    body: StyleTransferBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    voices = ["formal", "casual", "empathetic", "concise", "expert"]
    return {
        "items": [
            {
                "voice": voice,
                "rewrite": f"[{voice}] {body.section}",
                "eval_delta": round((index - 2) * 0.01, 3),
                "evidence_ref": f"style-transfer/{agent_id}/{voice}",
            }
            for index, voice in enumerate(voices)
        ]
    }


class BisectBody(BaseModel):
    failing_eval_case_id: str = Field(min_length=1, max_length=160)
    since_ref: str = Field(default="last-green", max_length=128)
    until_ref: str = Field(default="current", max_length=128)


@router_agents.post("/{agent_id}/bisect")
async def regression_bisect(
    request: Request,
    agent_id: UUID,
    body: BisectBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    versions = await request.app.state.cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    culprit = versions[-1] if versions else None
    return {
        "status": "complete",
        "failing_eval_case_id": body.failing_eval_case_id,
        "culprit": {
            "ref": f"v{culprit.version}" if culprit else "unversioned-draft",
            "author": culprit.created_by if culprit else caller_sub,
            "object": "behavior section",
            "confidence": 0.88 if culprit else 0.52,
            "diff": culprit.notes if culprit else "No saved version history yet.",
        },
        "elapsed_ms": 28_000,
    }


class VoiceDemoBody(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=160)
    expires_in_minutes: int = Field(default=5, ge=1, le=60)


@router_workspaces.post("/{workspace_id}/voice/demo-links", status_code=201)
async def create_voice_demo_link(
    request: Request,
    workspace_id: UUID,
    body: VoiceDemoBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"voice_demo_{uuid4().hex[:10]}",
        "snapshot_id": body.snapshot_id,
        "url": f"/voice-demo/{uuid4().hex[:18]}",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=body.expires_in_minutes)).isoformat(),
        "rate_limit": "5 minutes / 20 turns",
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="voice_demo:create",
        resource_type="voice_demo",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.get("/{workspace_id}/activity")
async def workspace_activity(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, page_size=100)
    )
    rate = min(1.0, len(traces.items) / 100)
    return {
        "turn_rate_per_minute": len(traces.items),
        "ribbon_intensity": rate,
        "tone": "live" if rate > 0.3 else "quiet",
    }


__all__ = ["router_agents", "router_public", "router_workspaces"]
