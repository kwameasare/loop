"""Conversation routes (P0.4).

* ``GET   /v1/agents/{id}/conversations`` — list (any member).
* ``GET   /v1/conversations/{id}`` — single read (any member).
* ``POST  /v1/conversations/{id}/takeover`` — operator takeover (ADMIN+).
* ``POST  /v1/conversations/{id}/operator-messages`` — operator reply (ADMIN+).
* ``POST  /v1/conversations/{id}/handback`` — return control to agent (ADMIN+).

The studio's `/inbox` page is the primary consumer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.conversations import (
    ConversationError,
    ConversationState,
    serialise_detail,
    serialise_message,
    serialise_summary,
)

router_agents_conv = APIRouter(prefix="/v1/agents", tags=["Conversations"])
router_conversations = APIRouter(prefix="/v1/conversations", tags=["Conversations"])


class TakeoverBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    note: str = Field(default="", max_length=2048)


class OperatorMessageBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    body: str = Field(min_length=1, max_length=4096)


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = cp.agents._agents.get(agent_id)  # type: ignore[attr-defined]
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


async def _conversation_workspace(request: Request, conversation_id: UUID) -> UUID:
    cp = request.app.state.cp
    summary = cp.conversations._summaries.get(conversation_id)  # type: ignore[attr-defined]
    if summary is None:
        raise HTTPException(status_code=404, detail="unknown conversation")
    return summary.workspace_id


@router_agents_conv.get("/{agent_id}/conversations")
async def list_agent_conversations(
    request: Request,
    agent_id: UUID,
    state: ConversationState | None = Query(default=None),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    rows = await cp.conversations.list_for_agent(
        workspace_id=workspace_id, agent_id=agent_id, state=state
    )
    return {"items": [serialise_summary(r) for r in rows]}


@router_conversations.get("/{conversation_id}")
async def get_conversation(
    request: Request,
    conversation_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _conversation_workspace(request, conversation_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        detail = await cp.conversations.get(
            workspace_id=workspace_id, conversation_id=conversation_id
        )
    except ConversationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialise_detail(detail)


@router_conversations.post("/{conversation_id}/takeover")
async def takeover_conversation(
    request: Request,
    conversation_id: UUID,
    body: TakeoverBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Operator takeover. ADMIN+ — agent should never be taken over by
    a regular member without explicit privilege."""
    cp = request.app.state.cp
    workspace_id = await _conversation_workspace(request, conversation_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        summary = await cp.conversations.takeover(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            operator_sub=caller_sub,
            note=body.note,
        )
    except ConversationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="conversation:takeover",
        resource_type="conversation",
        store=cp.audit_events,
        resource_id=str(conversation_id),
        request_id=request_id(request),
        # NEVER log the conversation content; only metadata.
        payload={
            "conversation_id": str(conversation_id),
            "agent_id": str(summary.agent_id),
            "state": summary.state,
        },
    )
    return serialise_summary(summary)


@router_conversations.post("/{conversation_id}/operator-messages", status_code=201)
async def post_operator_message(
    request: Request,
    conversation_id: UUID,
    body: OperatorMessageBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _conversation_workspace(request, conversation_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        message = await cp.conversations.operator_reply(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            body=body.body,
        )
    except ConversationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="conversation:operator_message",
        resource_type="conversation",
        store=cp.audit_events,
        resource_id=str(conversation_id),
        request_id=request_id(request),
        payload={
            "conversation_id": str(conversation_id),
            "message_id": str(message.id),
            "body_length": len(body.body),
        },
    )
    return serialise_message(message)


@router_conversations.post("/{conversation_id}/handback")
async def handback_conversation(
    request: Request,
    conversation_id: UUID,
    body: TakeoverBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    workspace_id = await _conversation_workspace(request, conversation_id)
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        summary = await cp.conversations.handback(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            operator_sub=caller_sub,
            note=body.note,
        )
    except ConversationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="conversation:handback",
        resource_type="conversation",
        store=cp.audit_events,
        resource_id=str(conversation_id),
        request_id=request_id(request),
        payload={
            "conversation_id": str(conversation_id),
            "agent_id": str(summary.agent_id),
            "state": summary.state,
        },
    )
    return serialise_summary(summary)


__all__ = ["router_agents_conv", "router_conversations"]
