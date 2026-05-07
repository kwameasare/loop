"""Agent tool catalog routes for Studio wire-up."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["AgentTools"])


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


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
        selected = next((version for version in versions if version.version == active_version), None)
    if selected is None:
        selected = versions[-1]
    return {"items": _tools_from_spec(selected.spec)}


__all__ = ["router"]
