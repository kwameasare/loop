from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from loop_control_plane._agent_route_utils import resolve_agent_for_route
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.agent_commitments import (
    CommitmentBody,
    commitment_payload,
    missing_required_fields,
)
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role

router = APIRouter(prefix="/v1/agents", tags=["AgentCommitments"])


class CommitmentDraftBody(BaseModel):
    body: CommitmentBody
    created_from: str = Field(default="studio:agent_contract", max_length=128)


async def _agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    workspace_id: UUID | None = None,
    required_role: Role | None = None,
) -> Any:
    return await resolve_agent_for_route(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=required_role,
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
        resource_type="commitment_document",
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


@router.get("/{agent_id}/commitment/current")
async def get_current_commitment(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )
    record = await request.app.state.cp.agent_commitments.current(agent=agent)
    return commitment_payload(record)


@router.get("/{agent_id}/commitments")
async def list_commitments(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
    )
    history = await request.app.state.cp.agent_commitments.history(agent=agent)
    return {"items": [commitment_payload(record) for record in history]}


@router.post("/{agent_id}/commitment", status_code=201)
async def save_commitment_draft(
    request: Request,
    agent_id: UUID,
    body: CommitmentDraftBody,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    record = await request.app.state.cp.agent_commitments.save_draft(
        agent=agent,
        body=body.body,
        created_from=body.created_from,
    )
    payload = commitment_payload(record)
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="commitment:draft_save",
        resource_id=record.id,
        payload={
            "agent_id": str(agent_id),
            "version": record.version,
            "content_hash": record.content_hash,
            "missing_required_fields": missing_required_fields(record.body),
        },
    )
    return payload


@router.post("/{agent_id}/commitment/accept")
async def accept_commitment(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
    workspace_id: UUID | None = None,
) -> dict[str, Any]:
    agent = await _agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        workspace_id=workspace_id,
        required_role=Role.ADMIN,
    )
    record = await request.app.state.cp.agent_commitments.accept_current(agent=agent)
    _audit(
        request,
        workspace_id=agent.workspace_id,
        caller_sub=caller_sub,
        action="commitment:accept",
        resource_id=record.id,
        payload={
            "agent_id": str(agent_id),
            "version": record.version,
            "content_hash": record.content_hash,
        },
    )
    return commitment_payload(record)
