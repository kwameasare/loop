"""Agent tool catalog routes for Studio wire-up."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.tool_call_telemetry import (
    ToolCallTelemetryInput,
)
from loop_control_plane.tool_contracts import (
    ToolContractUpsert,
    tool_contract_payload,
)

router = APIRouter(prefix="/v1/agents", tags=["AgentTools"])


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


async def _agent(request: Request, agent_id: UUID, caller_sub: str, *, admin: bool = False) -> Any:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=agent.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN if admin else None,
    )
    return agent


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_id: str,
    resource_type: str = "tool_contract",
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


def _tool_payload(raw: object, index: int) -> dict[str, Any]:
    if isinstance(raw, str):
        return {
            "id": raw,
            "name": raw,
            "kind": "mcp",
            "description": "",
            "source": "agent-version-spec",
        }
    if isinstance(raw, dict):
        name = str(raw.get("name") or raw.get("id") or f"tool-{index + 1}")
        kind = str(raw.get("kind") or raw.get("type") or "mcp")
        if kind not in {"mcp", "http"}:
            kind = "mcp"
        return {
            "id": str(raw.get("id") or name),
            "name": name,
            "kind": kind,
            "description": str(raw.get("description") or ""),
            "source": str(raw.get("source") or raw.get("url") or "agent-version-spec"),
        }
    return {
        "id": f"tool-{index + 1}",
        "name": f"tool-{index + 1}",
        "kind": "mcp",
        "description": "",
        "source": "agent-version-spec",
    }


def _tools_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tools = spec.get("tools", [])
    if isinstance(raw_tools, dict):
        raw_tools = raw_tools.get("items", [])
    if not isinstance(raw_tools, list):
        return []
    return [_tool_payload(raw, index) for index, raw in enumerate(raw_tools)]


@router.get("/{agent_id}/tools")
async def list_agent_tools(
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
    versions = await cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    if not versions:
        return {"items": []}
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    active_version = getattr(agent, "active_version", None)
    selected = None
    if active_version is not None:
        selected = next(
            (version for version in versions if version.version == active_version), None
        )
    if selected is None:
        selected = versions[-1]
    return {"items": _tools_from_spec(selected.spec)}


@router.get("/{agent_id}/tool-contracts")
async def list_tool_contracts(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub)
    contracts = await request.app.state.cp.tool_contracts.list_for_agent(agent=agent)
    return {"items": [tool_contract_payload(contract) for contract in contracts]}


@router.get("/{agent_id}/tool-contracts/metrics")
async def list_tool_contract_metrics(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub)
    contracts = await request.app.state.cp.tool_contracts.list_for_agent(agent=agent)
    metrics = request.app.state.cp.tool_call_telemetry.metrics_for_agent(
        agent=agent,
        contracts=contracts,
    )
    return {"items": [item.model_dump(mode="json") for item in metrics]}


@router.post("/{agent_id}/tools/{tool_id}/calls")
async def record_tool_call_telemetry(
    request: Request,
    agent_id: UUID,
    tool_id: str,
    body: ToolCallTelemetryInput,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub)
    record = request.app.state.cp.tool_call_telemetry.record(
        agent=agent,
        tool_id=tool_id,
        body=body,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="tool_call:record",
        resource_type="tool_call",
        resource_id=tool_id,
        payload={
            "agent_id": str(agent_id),
            "trace_id": body.trace_id,
            "status": body.status,
            "latency_ms": body.latency_ms,
            "retry_count": body.retry_count,
            "pii_sent": body.pii_sent,
        },
    )
    return record.model_dump(mode="json")


@router.put("/{agent_id}/tool-contracts/{tool_id}")
async def upsert_tool_contract(
    request: Request,
    agent_id: UUID,
    tool_id: str,
    body: ToolContractUpsert,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    contract = await request.app.state.cp.tool_contracts.upsert(
        agent=agent,
        tool_id=tool_id,
        body=body,
    )
    invalidated = await request.app.state.cp.preapproved_classes.invalidate_for_change_types(
        agent=agent,
        change_types=["tool"],
        reason=f"Tool contract {contract.id} changed.",
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="tool_contract:upsert",
        resource_id=contract.id,
        payload={
            "agent_id": str(agent_id),
            "tool_id": tool_id,
            "live_status": contract.live_status,
            "approval_invalidated_at": contract.approval_invalidated_at.isoformat()
            if contract.approval_invalidated_at
            else None,
            "invalidated_pre_approved_classes": [record.id for record in invalidated],
        },
    )
    return tool_contract_payload(contract)


@router.post("/{agent_id}/tool-contracts/{tool_id}/promote")
async def promote_tool_contract(
    request: Request,
    agent_id: UUID,
    tool_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _agent(request, agent_id, caller_sub, admin=True)
    contract = await request.app.state.cp.tool_contracts.promote(
        agent=agent,
        tool_id=tool_id,
    )
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="tool_contract:promote",
        resource_id=contract.id,
        payload={
            "agent_id": str(agent_id),
            "tool_id": tool_id,
            "content_hash": contract.content_hash,
        },
    )
    return tool_contract_payload(contract)


__all__ = ["router"]
