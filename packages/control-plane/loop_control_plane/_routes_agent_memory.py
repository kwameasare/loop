"""Agent memory routes for Studio Memory Studio wire-up."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from loop_memory.models import MemoryEntry

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access

router = APIRouter(prefix="/v1/agents", tags=["Memory"])


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


def _safe_preview(value: object) -> str:
    rendered = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    if any(token in rendered.lower() for token in ("secret", "token", "password", "card")):
        return "[redacted secret-like value]"
    return rendered if len(rendered) <= 160 else f"{rendered[:157]}..."


def _serialise_memory(entry: MemoryEntry) -> dict[str, Any]:
    user_id = entry.user_id or "bot"
    return {
        "id": f"{entry.scope.value}:{user_id}:{entry.key}",
        "workspace_id": str(entry.workspace_id),
        "agent_id": str(entry.agent_id),
        "scope": entry.scope.value,
        "user_id": entry.user_id,
        "key": entry.key,
        "before": "unknown",
        "after": _safe_preview(entry.value),
        "source": "runtime memory store",
        "source_trace": "not-attached",
        "retention_policy": "durable user memory; delete with audit trail",
        "updated_at": entry.updated_at.isoformat(),
        "writer_version": "live",
        "confidence": "medium",
        "safety_flags": ["none"],
        "deletion_state": "available",
        "deletion_reason": "User memory can be deleted with audit trail.",
        "replay_impact": "Replay without this memory removes the stored preference or fact.",
    }


@router.get("/{agent_id}/memory")
async def list_agent_memory(
    request: Request,
    agent_id: UUID,
    user_id: str | None = Query(default=None),
    conversation_id: UUID | None = Query(default=None),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    target_user_id = user_id or caller_sub
    entries = [
        _serialise_memory(entry)
        for entry in await cp.user_memory_store.list_user(
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=target_user_id,
        )
    ]
    if conversation_id is not None:
        session = await cp.session_memory_store.all(conversation_id=conversation_id)
        entries.extend(
            {
                "id": f"session:{conversation_id}:{key}",
                "workspace_id": str(workspace_id),
                "agent_id": str(agent_id),
                "scope": "session",
                "user_id": target_user_id,
                "key": key,
                "before": "unknown",
                "after": _safe_preview(value),
                "source": "runtime session memory store",
                "source_trace": "not-attached",
                "retention_policy": "session memory; expires with conversation TTL",
                "updated_at": "",
                "writer_version": "live",
                "confidence": "medium",
                "safety_flags": ["none"],
                "deletion_state": "blocked",
                "deletion_reason": "Session memory expires automatically.",
                "replay_impact": "Replay without session memory clears this temporary state.",
            }
            for key, value in sorted(session.items())
        )
    return {"items": entries}


@router.delete("/{agent_id}/memory/user/{memory_key}", status_code=204)
async def delete_user_memory(
    request: Request,
    agent_id: UUID,
    memory_key: str,
    user_id: str | None = Query(default=None),
    caller_sub: str = CALLER,
) -> Response:
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    target_user_id = user_id or caller_sub
    deleted = await cp.user_memory_store.delete_user(
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=target_user_id,
        key=memory_key,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="memory entry not found")
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="memory:delete",
        resource_type="memory_entry",
        store=cp.audit_events,
        resource_id=f"user:{target_user_id}:{memory_key}",
        request_id=request_id(request),
    )
    return Response(status_code=204)


__all__ = ["router"]
