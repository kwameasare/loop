"""Workspace secrets routes (P0.4 + P0.7a).

The :class:`SecretsBackend` Protocol is provider-agnostic (Vault,
AWS Secrets Manager, Azure KV, GCP SM, AliCloud KMS). The routes here
namespace each secret reference under
``workspace/{workspace_id}/{name}`` so two workspaces can use the
same logical secret name without cross-tenant collision in the
backend.

ADMIN-only for write paths; any member can READ a secret value
(workspace agents need this — secrets are how operators give the
agent a per-workspace API key without exposing it via env var).

The plaintext secret value is NEVER recorded in audit payloads —
only the ref name, the version (returned from set/rotate), and the
operation type. Audit reviewers can prove "alice rotated FOO at T"
without seeing what FOO became.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.secrets import SecretsBackendError

router = APIRouter(prefix="/v1/workspaces", tags=["Secrets"])


class SecretSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: str = Field(min_length=1)
    ttl_seconds: int | None = Field(default=None, ge=1)


class SecretRotateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    new_value: str = Field(min_length=1)


def _ref(workspace_id: UUID, name: str) -> str:
    """Compose the cross-workspace-safe backend ref."""
    return f"workspace/{workspace_id}/{name}"


@router.put("/{workspace_id}/secrets/{name}")
async def set_secret(
    request: Request,
    workspace_id: UUID,
    name: str,
    body: SecretSetRequest,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Create or replace a secret. ADMIN-only.

    Returns the new version number. The plaintext is never echoed back
    in the response — caller already has it.
    """
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    if not name or "/" in name or len(name) > 128:
        raise HTTPException(
            status_code=400, detail="secret name must be 1-128 chars and not contain '/'"
        )
    try:
        version = cp.secrets_backend.set(
            _ref(workspace_id, name), body.value, ttl_seconds=body.ttl_seconds
        )
    except SecretsBackendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:secret:set",
        resource_type="secret",
        store=cp.audit_events,
        resource_id=name,
        request_id=request_id(request),
        # NEVER log the value.
        payload={"name": name, "version": version},
    )
    return {"name": name, "version": version}


@router.get("/{workspace_id}/secrets/{name}")
async def get_secret(
    request: Request,
    workspace_id: UUID,
    name: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Read a secret. Any workspace member can read.

    The audit row records the read operation but NOT the plaintext —
    this lets compliance review who read what, when, without
    materialising the value in the audit log itself.
    """
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        value = cp.secrets_backend.get(_ref(workspace_id, name))
    except SecretsBackendError as exc:
        raise HTTPException(status_code=404, detail="secret not found") from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:secret:get",
        resource_type="secret",
        store=cp.audit_events,
        resource_id=name,
        request_id=request_id(request),
        payload={"name": name},
    )
    return {"name": name, "value": value}


@router.post("/{workspace_id}/secrets/{name}/rotate")
async def rotate_secret(
    request: Request,
    workspace_id: UUID,
    name: str,
    body: SecretRotateRequest,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Rotate a secret to a new value, bumping the version. ADMIN-only."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        version = cp.secrets_backend.rotate(_ref(workspace_id, name), body.new_value)
    except SecretsBackendError as exc:
        raise HTTPException(status_code=404, detail="secret not found") from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:secret:rotate",
        resource_type="secret",
        store=cp.audit_events,
        resource_id=name,
        request_id=request_id(request),
        payload={"name": name, "version": version},
    )
    return {"name": name, "version": version}


@router.delete("/{workspace_id}/secrets/{name}", status_code=204)
async def delete_secret(
    request: Request,
    workspace_id: UUID,
    name: str,
    caller_sub: str = CALLER,
) -> None:
    """Delete a secret. ADMIN-only."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        cp.secrets_backend.delete(_ref(workspace_id, name))
    except SecretsBackendError as exc:
        raise HTTPException(status_code=404, detail="secret not found") from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:secret:delete",
        resource_type="secret",
        store=cp.audit_events,
        resource_id=name,
        request_id=request_id(request),
        payload={"name": name},
    )
    # 204 No Content


__all__ = ["router"]
