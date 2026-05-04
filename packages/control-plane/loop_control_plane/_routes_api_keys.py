"""Workspace API-key routes (P0.4 + P0.7a).

`ApiKeyAPI` already implements `create`, `list_for_workspace`, and
`revoke`. This module is the FastAPI shim. Plaintext is shown exactly
once on creation; the list endpoint and the stored row never expose
it again.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, JSON_BODY, request_id
from loop_control_plane.api_keys import ApiKeyError
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.audit_redaction import redact_for_audit

router = APIRouter(prefix="/v1/workspaces", tags=["ApiKeys"])


@router.get("/{workspace_id}/api-keys")
async def list_api_keys(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Any workspace member can list keys (no plaintext)."""
    return await request.app.state.cp.api_key_api.list_for_workspace(
        caller_sub=caller_sub, workspace_id=workspace_id
    )


@router.post("/{workspace_id}/api-keys", status_code=201)
async def create_api_key(
    request: Request,
    workspace_id: UUID,
    body: dict[str, Any] = JSON_BODY,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Issue a new API key. ADMIN-only. Plaintext shown once."""
    runtime = request.app.state.cp
    issued = await runtime.api_key_api.create(
        caller_sub=caller_sub, workspace_id=workspace_id, body=body
    )
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:api_key:create",
        resource_type="api_key",
        store=runtime.audit_events,
        resource_id=str(issued.get("id", "")),
        request_id=request_id(request),
        payload=redact_for_audit(
            {
                "id": issued.get("id"),
                "name": issued.get("name"),
                "prefix": issued.get("prefix"),
                "plaintext": issued.get("plaintext"),
            }
        ),
    )
    return issued


@router.delete("/{workspace_id}/api-keys/{key_id}", status_code=200)
async def revoke_api_key(
    request: Request,
    workspace_id: UUID,
    key_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Revoke a key. ADMIN-only. Idempotent."""
    runtime = request.app.state.cp
    try:
        revoked = await runtime.api_key_api.revoke(
            caller_sub=caller_sub, workspace_id=workspace_id, key_id=key_id
        )
    except ApiKeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:api_key:revoke",
        resource_type="api_key",
        store=runtime.audit_events,
        resource_id=str(key_id),
        request_id=request_id(request),
        payload={"id": str(key_id)},
    )
    return revoked


__all__ = ["router"]
