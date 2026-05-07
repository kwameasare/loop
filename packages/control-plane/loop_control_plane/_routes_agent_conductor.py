"""Multi-agent conductor routes for Studio wire-up."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["Conductor"])

_OBJECT_STATES = {"draft", "saved", "staged", "canary", "production", "archived"}
_TRUST_STATES = {"healthy", "watching", "drifting", "degraded", "blocked"}
_AGENT_STATUSES = {"ready", "active", "degraded", "blocked"}
_HANDOFF_STATES = {"ready", "active", "violated", "blocked"}
_CONFIDENCE_LEVELS = {"high", "medium", "low", "unsupported"}


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


def _choice(value: object, allowed: set[str], default: str) -> str:
    normalized = str(value) if value is not None else ""
    return normalized if normalized in allowed else default


def _sub_agent(raw: object, index: int) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    name = str(data.get("name") or data.get("id") or f"Sub-agent {index + 1}")
    sub_id = str(data.get("id") or f"sub_agent_{index + 1}")
    return {
        "id": sub_id,
        "name": name,
        "purpose": str(data.get("purpose") or "Declared in the agent version spec."),
        "owner": str(data.get("owner") or "Workspace"),
        "version": str(data.get("version") or "draft"),
        "objectState": _choice(data.get("objectState"), _OBJECT_STATES, "draft"),
        "trust": _choice(data.get("trust"), _TRUST_STATES, "watching"),
        "status": _choice(data.get("status"), _AGENT_STATUSES, "ready"),
        "currentOwner": str(data.get("currentOwner") or "Workspace"),
        "tools": data.get("tools") if isinstance(data.get("tools"), list) else [],
        "budgetUsd": float(data.get("budgetUsd") or 0),
        "spentUsd": float(data.get("spentUsd") or 0),
        "latencyP95Ms": int(data.get("latencyP95Ms") or 0),
        "evalCoveragePercent": int(data.get("evalCoveragePercent") or 0),
        "evalConfidence": _choice(
            data.get("evalConfidence"), _CONFIDENCE_LEVELS, "unsupported"
        ),
        "memoryAccess": str(data.get("memoryAccess") or "not declared"),
        "activeHandoffs": int(data.get("activeHandoffs") or 0),
        "costEvidence": str(data.get("costEvidence") or "not recorded"),
        "latencyEvidence": str(data.get("latencyEvidence") or "not recorded"),
        "failurePaths": data.get("failurePaths")
        if isinstance(data.get("failurePaths"), list)
        else [],
        "traceSpans": data.get("traceSpans") if isinstance(data.get("traceSpans"), list) else [],
    }


def _contract(raw: object, index: int) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    return {
        "id": str(data.get("id") or f"contract_{index + 1}"),
        "name": str(data.get("name") or f"Handoff contract {index + 1}"),
        "from": str(data.get("from") or "source"),
        "to": str(data.get("to") or "target"),
        "purpose": str(data.get("purpose") or "Declared in the agent version spec."),
        "state": _choice(data.get("state"), _HANDOFF_STATES, "ready"),
        "inputSchema": data.get("inputSchema") if isinstance(data.get("inputSchema"), list) else [],
        "outputSchema": data.get("outputSchema")
        if isinstance(data.get("outputSchema"), list)
        else [],
        "timeoutMs": int(data.get("timeoutMs") or 1000),
        "fallback": str(data.get("fallback") or "Return control to the parent agent."),
        "memoryAccess": str(data.get("memoryAccess") or "not declared"),
        "toolGrants": data.get("toolGrants") if isinstance(data.get("toolGrants"), list) else [],
        "budgetUsd": float(data.get("budgetUsd") or 0),
        "currentOwner": str(data.get("currentOwner") or "Workspace"),
        "evidenceTrace": str(data.get("evidenceTrace") or "not-attached"),
        **({"violation": str(data["violation"])} if data.get("violation") else {}),
    }


@router.get("/{agent_id}/conductor")
async def get_agent_conductor(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    agent = cp.agents._agents[agent_id]  # type: ignore[attr-defined]
    versions = await cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    selected = versions[-1] if versions else None
    spec = selected.spec if selected is not None else {}
    sub_agents_raw = spec.get("sub_agents", [])
    contracts_raw = spec.get("handoff_contracts", [])
    sub_agents = [
        _sub_agent(raw, index)
        for index, raw in enumerate(sub_agents_raw if isinstance(sub_agents_raw, list) else [])
    ]
    contracts = [
        _contract(raw, index)
        for index, raw in enumerate(contracts_raw if isinstance(contracts_raw, list) else [])
    ]
    return {
        "agentId": str(agent_id),
        "agentName": agent.name,
        "branch": f"v{selected.version}" if selected is not None else "draft",
        "objectState": "saved" if selected is not None else "draft",
        "trust": "healthy" if sub_agents else "watching",
        "subAgents": sub_agents,
        "contracts": contracts,
        "delegations": [],
        "topology": [
            {
                "id": f"edge_{index + 1}",
                "source": str(contract["from"]),
                "target": str(contract["to"]),
                "label": str(contract["state"]),
                "state": str(contract["state"]),
            }
            for index, contract in enumerate(contracts)
        ],
        "orchestrationEvidence": f"agent {agent_id}; version {selected.version if selected else 'none'}",
        **(
            {}
            if sub_agents
            else {
                "degradedReason": "No sub-agent topology is declared on the active or latest agent version."
            }
        ),
    }


__all__ = ["router"]
