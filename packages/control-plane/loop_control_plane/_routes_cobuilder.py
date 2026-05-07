"""AI Co-Builder route for Studio wire-up.

The co-builder surface is intentionally diagnostic: it reads workspace,
agent, and version state, then returns bounded suggestions with consent
metadata. It does not mutate the agent; apply remains a separate, gated
workflow owned by the target surface.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.workspaces import Role

router = APIRouter(prefix="/v1/workspaces", tags=["CoBuilder"])


def _mode_for_role(role: Role) -> str:
    if role in (Role.OWNER, Role.ADMIN):
        return "drive"
    if role is Role.MEMBER:
        return "edit"
    return "suggest"


def _scopes_for_role(role: Role) -> list[str]:
    if role in (Role.OWNER, Role.ADMIN):
        return [
            "agent:edit",
            "flow:write",
            "kb:rebuild",
            "tools:write",
            "eval:write",
        ]
    if role is Role.MEMBER:
        return ["agent:edit", "flow:write", "eval:write"]
    return ["agent:read"]


def _first_string(spec: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _labels(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            for key in ("name", "id", "key", "label"):
                label = item.get(key)
                if isinstance(label, str) and label.strip():
                    out.append(label.strip())
                    break
    return out


def _list_from_spec(spec: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        labels = _labels(spec.get(key))
        if labels:
            seen: set[str] = set()
            unique: list[str] = []
            for label in labels:
                if label in seen:
                    continue
                seen.add(label)
                unique.append(label)
            return unique
    return []


def _risk_tool(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "refund",
            "charge",
            "payment",
            "delete",
            "write",
            "send",
            "email",
            "sms",
            "transfer",
            "payout",
        )
    )


def _action(
    *,
    action_id: str,
    mode: str,
    title: str,
    rationale: str,
    path: str,
    body: str,
    provenance: list[dict[str, str]],
    usd: float,
    latency_ms: int,
    scopes: list[str],
    evidence_ref: str,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "mode": mode,
        "title": title,
        "rationale": rationale,
        "diff": {"path": path, "body": body},
        "provenance": provenance,
        "cost": {"usd": usd, "latencyMs": latency_ms},
        "requiredScopes": scopes,
        "evidenceRef": evidence_ref,
    }


def _fallback_action(
    *, agent_id: UUID, version_label: str, prompt: str
) -> dict[str, Any]:
    body = (
        "@@ behavior\n"
        "+ Require every answer to cite the policy, trace, tool result, or memory rule that changed it."
    )
    if prompt:
        body = "@@ behavior\n+ Add replay coverage for the edited behavior before promotion."
    return _action(
        action_id="act_replay_before_promote",
        mode="suggest",
        title="Replay production-like turns before promoting this version",
        rationale=(
            "The latest version needs a replay-backed confidence check before it becomes "
            "a production change."
        ),
        path=f"agents/{agent_id}/versions/{version_label}/evals.yaml",
        body=body,
        provenance=[
            {
                "source": f"agent version {version_label}",
                "excerpt": "Co-builder suggestions are derived from the saved agent version.",
                "evidenceRef": f"audit/cobuilder/{agent_id}/{version_label}/version",
            }
        ],
        usd=0.05,
        latency_ms=480,
        scopes=["eval:write"],
        evidence_ref=f"audit/cobuilder/{agent_id}/{version_label}/replay",
    )


def _build_payload(
    *,
    workspace_id: UUID,
    caller_sub: str,
    role: Role,
    agent: Any | None,
    latest_version: Any | None,
) -> dict[str, Any]:
    agent_id = getattr(agent, "id", None)
    agent_name = getattr(agent, "name", "No agent selected")
    version_label = f"v{getattr(latest_version, 'version', 0) or 0}"
    spec = getattr(latest_version, "spec", {}) if latest_version is not None else {}
    if not isinstance(spec, dict):
        spec = {}
    prompt = _first_string(spec, ("system_prompt", "prompt", "instructions", "behavior"))
    tools = _list_from_spec(spec, ("tools", "tool_ids", "tool_grants"))
    memory_rules = _list_from_spec(spec, ("memory", "memory_rules", "memory_policies"))
    risky_tools = [tool for tool in tools if _risk_tool(tool)]
    evidence_base = f"audit/cobuilder/{workspace_id}/{agent_id or 'none'}"

    actions: list[dict[str, Any]] = []
    if agent_id is not None and not prompt:
        actions.append(
            _action(
                action_id="act_add_behavior_instructions",
                mode="edit",
                title="Add explicit behavior instructions before the next preview",
                rationale=(
                    "The saved version does not expose a system prompt or instruction field, "
                    "so trace explanations cannot connect behavior to source text."
                ),
                path=f"agents/{agent_id}/behavior.yaml",
                body=(
                    "@@ behavior\n"
                    "+ Goal: answer only with policy-backed evidence.\n"
                    "+ Constraint: cite the trace span, tool result, or memory rule that changed the answer.\n"
                    "+ Escalation: route legal threats and payment disputes to the human inbox."
                ),
                provenance=[
                    {
                        "source": f"{agent_name} {version_label}",
                        "excerpt": "No system_prompt, prompt, instructions, or behavior field was found.",
                        "evidenceRef": f"{evidence_base}/missing_prompt",
                    }
                ],
                usd=0.02,
                latency_ms=120,
                scopes=["agent:edit", "flow:write"],
                evidence_ref=f"{evidence_base}/act_add_behavior_instructions",
            )
        )
    if agent_id is not None and risky_tools:
        tool = risky_tools[0]
        actions.append(
            _action(
                action_id="act_gate_side_effect_tool",
                mode="edit",
                title=f"Gate side-effect tool `{tool}` with preview and approval",
                rationale=(
                    "A side-effect capable tool is present in the latest version. It should "
                    "stay behind safety-contract, replay, and rollback gates."
                ),
                path=f"agents/{agent_id}/tools/{tool}.yaml",
                body=(
                    "@@ safety_contract\n"
                    "+ preview_required: true\n"
                    "+ approval_required: true\n"
                    "+ rollback_on: [eval_regression, cost_spike, tool_error_rate]\n"
                    "+ production_apply: gated"
                ),
                provenance=[
                    {
                        "source": f"{agent_name} {version_label}",
                        "excerpt": f"Tool `{tool}` matched side-effect risk heuristics.",
                        "evidenceRef": f"{evidence_base}/tools/{tool}",
                    }
                ],
                usd=0.04,
                latency_ms=260,
                scopes=["agent:edit", "tools:write"],
                evidence_ref=f"{evidence_base}/act_gate_side_effect_tool",
            )
        )
    if agent_id is not None:
        actions.append(
            _fallback_action(agent_id=agent_id, version_label=version_label, prompt=prompt)
        )

    if not actions:
        actions.append(
            _action(
                action_id="act_create_first_agent",
                mode="suggest",
                title="Create an agent before running Co-Builder diagnostics",
                rationale="Co-Builder needs at least one agent and saved version to produce grounded diffs.",
                path="workspace/agents",
                body="@@ agents\n+ Create an agent and save v1 before asking Co-Builder to review behavior.",
                provenance=[
                    {
                        "source": "workspace agents",
                        "excerpt": "No agent was available in this workspace.",
                        "evidenceRef": f"{evidence_base}/empty_workspace",
                    }
                ],
                usd=0,
                latency_ms=0,
                scopes=["agent:read"],
                evidence_ref=f"{evidence_base}/act_create_first_agent",
            )
        )

    primary = actions[0]
    review_bullets = [
        {
            "id": "rb_prompt",
            "severity": "block" if not prompt and agent_id is not None else "info",
            "body": (
                "Behavior instructions are missing from the latest version."
                if not prompt and agent_id is not None
                else "Behavior instructions are present and can be traced to this saved version."
            ),
            "evidenceRef": f"{evidence_base}/review/prompt",
        },
        {
            "id": "rb_tools",
            "severity": "warn" if risky_tools else "info",
            "body": (
                f"Side-effect capable tools need safety contracts: {', '.join(risky_tools)}."
                if risky_tools
                else "No side-effect capable tools were detected in the version spec."
            ),
            "evidenceRef": f"{evidence_base}/review/tools",
        },
        {
            "id": "rb_memory",
            "severity": (
                "warn"
                if any(
                    token in rule.lower()
                    for rule in memory_rules
                    for token in ("secret", "payment", "card", "password", "token")
                )
                else "info"
            ),
            "body": (
                "Memory rules mention sensitive-data terms; verify retention before durable writes."
                if memory_rules
                else "No memory rules are declared yet; Memory Studio will show no writes."
            ),
            "evidenceRef": f"{evidence_base}/review/memory",
        },
        {
            "id": "rb_eval",
            "severity": "warn",
            "body": "Replay this change against production-like conversations before promotion.",
            "evidenceRef": f"{evidence_base}/review/eval",
        },
        {
            "id": "rb_consent",
            "severity": "info",
            "body": f"{caller_sub} is operating in {_mode_for_role(role)} mode from workspace role `{role.value}`.",
            "evidenceRef": f"{evidence_base}/review/consent",
        },
    ]

    return {
        "workspaceId": str(workspace_id),
        "agentId": str(agent_id) if agent_id is not None else None,
        "agentName": agent_name,
        "operator": {
            "maxMode": _mode_for_role(role),
            "scopes": _scopes_for_role(role),
            "budgetRemainingUsd": 5.0 if role in (Role.OWNER, Role.ADMIN) else 1.0,
        },
        "actions": actions,
        "rubberDuck": {
            "caseId": f"rd_{str(agent_id or workspace_id)[:8]}",
            "failureSummary": (
                "Co-Builder found a behavior-wire-up issue in the latest version."
                if not prompt or risky_tools
                else "Co-Builder did not find a blocker; replay still recommended before promotion."
            ),
            "findings": [
                {
                    "step": "version.spec",
                    "observation": f"Read {agent_name} {version_label} as the grounding source.",
                    "evidenceRef": f"{evidence_base}/rubberduck/version",
                },
                {
                    "step": "behavior.instructions",
                    "observation": (
                        "Instructions are missing."
                        if not prompt and agent_id is not None
                        else "Instructions are present."
                    ),
                    "evidenceRef": f"{evidence_base}/rubberduck/prompt",
                },
                {
                    "step": "tool_grants",
                    "observation": (
                        f"Side-effect tools detected: {', '.join(risky_tools)}."
                        if risky_tools
                        else "No side-effect tools detected."
                    ),
                    "evidenceRef": f"{evidence_base}/rubberduck/tools",
                },
            ],
            "proposedFix": primary,
        },
        "review": {
            "actionId": primary["id"],
            "bullets": review_bullets,
        },
    }


@router.get("/{workspace_id}/cobuilder")
async def get_cobuilder_workspace(
    request: Request,
    workspace_id: UUID,
    agent_id: UUID | None = Query(default=None),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    _, membership = await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    agents = await cp.agents.list_for_workspace(workspace_id)
    agent = None
    if agent_id is not None:
        agent = next((candidate for candidate in agents if candidate.id == agent_id), None)
        if agent is None:
            raise HTTPException(status_code=404, detail="unknown agent")
    elif agents:
        agent = agents[0]

    latest_version = None
    if agent is not None:
        versions = await cp.agent_versions.list_for_agent(
            workspace_id=workspace_id,
            agent_id=agent.id,
        )
        latest_version = max(versions, key=lambda version: version.version, default=None)

    return _build_payload(
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        role=membership.role,
        agent=agent,
        latest_version=latest_version,
    )


__all__ = ["router"]
