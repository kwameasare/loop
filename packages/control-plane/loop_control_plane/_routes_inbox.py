"""Operator inbox routes for Studio wire-up.

The inbox domain service already models escalation, claim, release, and
resolution. This FastAPI adapter makes that state machine available to Studio
instead of forcing the UI to fall back to an empty queue.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.inbox import InboxError

router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["Inbox"])
router_inbox = APIRouter(prefix="/v1/inbox", tags=["Inbox"])


class EscalateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: UUID
    conversation_id: UUID
    user_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    last_message_excerpt: str = ""
    now_ms: int | None = Field(default=None, ge=0)


class ClaimBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operator_id: str | None = None
    now_ms: int | None = Field(default=None, ge=0)


class ResolveBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    now_ms: int | None = Field(default=None, ge=0)


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _map_inbox_error(exc: InboxError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=409, detail=message)


@router_workspaces.get("/{workspace_id}/inbox")
async def list_inbox(
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
    pending = cp.inbox_api.list_pending(workspace_id=workspace_id)["items"]
    claimed = [
        item.model_dump(mode="json")
        for item in cp.inbox_queue.list_claimed_by(caller_sub)
        if item.workspace_id == workspace_id
    ]
    return {"items": [*pending, *claimed]}


@router_workspaces.post("/{workspace_id}/inbox/escalate", status_code=201)
async def escalate_to_inbox(
    request: Request,
    workspace_id: UUID,
    body: EscalateBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        item = cp.inbox_api.escalate(
            workspace_id=workspace_id,
            body={
                "agent_id": str(body.agent_id),
                "conversation_id": str(body.conversation_id),
                "user_id": body.user_id,
                "reason": body.reason,
                "now_ms": body.now_ms if body.now_ms is not None else _now_ms(),
                "last_message_excerpt": body.last_message_excerpt,
            },
        )
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="inbox:escalate",
        resource_type="inbox_item",
        store=cp.audit_events,
        resource_id=str(item["id"]),
        request_id=request_id(request),
        payload={
            "agent_id": str(body.agent_id),
            "conversation_id": str(body.conversation_id),
            "reason": body.reason,
        },
    )
    return item


@router_inbox.post("/{item_id}/claim")
async def claim_inbox_item(
    request: Request,
    item_id: UUID,
    body: ClaimBody | None = None,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    try:
        existing = cp.inbox_queue.get(item_id)
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=existing.workspace_id,
        user_sub=caller_sub,
    )
    claim_body = body or ClaimBody()
    try:
        item = cp.inbox_api.claim(
            item_id=item_id,
            body={
                "operator_id": claim_body.operator_id or caller_sub,
                "now_ms": claim_body.now_ms if claim_body.now_ms is not None else _now_ms(),
            },
        )
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    record_audit_event(
        workspace_id=existing.workspace_id,
        actor_sub=caller_sub,
        action="inbox:claim",
        resource_type="inbox_item",
        store=cp.audit_events,
        resource_id=str(item_id),
        request_id=request_id(request),
    )
    return item


@router_inbox.post("/{item_id}/release")
async def release_inbox_item(
    request: Request,
    item_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    try:
        existing = cp.inbox_queue.get(item_id)
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=existing.workspace_id,
        user_sub=caller_sub,
    )
    try:
        item = cp.inbox_api.release(item_id=item_id)
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    record_audit_event(
        workspace_id=existing.workspace_id,
        actor_sub=caller_sub,
        action="inbox:release",
        resource_type="inbox_item",
        store=cp.audit_events,
        resource_id=str(item_id),
        request_id=request_id(request),
    )
    return item


@router_inbox.post("/{item_id}/resolve")
async def resolve_inbox_item(
    request: Request,
    item_id: UUID,
    body: ResolveBody | None = None,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    try:
        existing = cp.inbox_queue.get(item_id)
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=existing.workspace_id,
        user_sub=caller_sub,
    )
    resolve_body = body or ResolveBody()
    try:
        item = cp.inbox_api.resolve(
            item_id=item_id,
            body={
                "now_ms": resolve_body.now_ms if resolve_body.now_ms is not None else _now_ms(),
            },
        )
    except InboxError as exc:
        raise _map_inbox_error(exc) from exc
    record_audit_event(
        workspace_id=existing.workspace_id,
        actor_sub=caller_sub,
        action="inbox:resolve",
        resource_type="inbox_item",
        store=cp.audit_events,
        resource_id=str(item_id),
        request_id=request_id(request),
    )
    return item


__all__ = ["router_inbox", "router_workspaces"]
