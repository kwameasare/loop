"""GDPR / CCPA Data Subject Request endpoints (P0.8b).

Wires the existing service module ``data_deletion.py`` into FastAPI
routes so the DPA template's commitments are actually serviceable:

* ``POST   /v1/workspaces/{workspace_id}/data-deletion`` — Art-17
  erasure: enqueue a tenant-data deletion request.
* ``GET    /v1/workspaces/{workspace_id}/data-deletion`` — list this
  workspace's deletion requests + their states (audit + studio
  Privacy tab).
* ``GET    /v1/workspaces/{workspace_id}/data-deletion/{request_id}``
  — single-row read, used by the studio while polling for completion.

Authorisation
=============
POST requires workspace OWNER. GET requires any membership (DPOs
need read-only).

Audit
=====
Every state-changing request emits an audit event so SOC2 CC7.3
evidence is concrete.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.data_deletion import (
    DataDeletionError,
    DataDeletionRequest,
    enqueue_data_deletion,
)

router = APIRouter(prefix="/v1/workspaces", tags=["DSR"])


class DataDeletionEnqueueBody(BaseModel):
    """Body for POST /v1/workspaces/{id}/data-deletion."""

    model_config = ConfigDict(extra="forbid", strict=True)
    requested_by_email: EmailStr = Field(
        description=(
            "Email to receive completion notification. Must match the "
            "caller's IdP claim — operators handling DSRs on behalf of "
            "a customer set this to their CS-team alias."
        )
    )


def _serialise(req: DataDeletionRequest) -> dict[str, object]:
    return {
        "id": str(req.id),
        "workspace_id": str(req.workspace_id),
        "requested_by_sub": req.requested_by_sub,
        "requested_by_email": req.requested_by_email,
        "requested_at": req.requested_at.isoformat(),
        "state": req.state.value,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "rows_deleted": req.rows_deleted,
        "failure_reason": req.failure_reason,
    }


@router.post(
    "/{workspace_id}/data-deletion",
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_workspace_deletion(
    workspace_id: UUID,
    body: DataDeletionEnqueueBody,
    request: Request,
    caller_sub: str = CALLER,
) -> dict[str, object]:
    """Art-17 erasure entry point.

    Idempotent: if a pending request already exists for this workspace,
    the existing request is returned with HTTP 202 and no new job is
    enqueued.
    """
    cp = request.app.state.cp
    # Owner-only — the only person allowed to nuke workspace data.
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.OWNER,
    )

    try:
        req = enqueue_data_deletion(
            workspace_id=workspace_id,
            requested_by_sub=caller_sub,
            requested_by_email=str(body.requested_by_email),
            store=cp.data_deletion_store,
            job_queue=cp.data_deletion_queue,
        )
    except DataDeletionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="workspace:data_deletion:enqueue",
        resource_type="data_deletion_request",
        store=cp.audit_events,
        resource_id=str(req.id),
        request_id=request_id(request),
        payload={
            "request_id": str(req.id),
            "state": req.state.value,
            "requested_by_email": req.requested_by_email,
        },
    )
    return _serialise(req)


@router.get("/{workspace_id}/data-deletion")
async def list_workspace_deletions(
    workspace_id: UUID,
    request: Request,
    caller_sub: str = CALLER,
) -> dict[str, list[dict[str, object]]]:
    """List all data-deletion requests for a workspace (any state)."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        # Any member can READ deletion-request status.
        required_role=None,
    )
    rows = cp.data_deletion_store.list_for_workspace(workspace_id)
    return {"requests": [_serialise(r) for r in rows]}


@router.get("/{workspace_id}/data-deletion/{request_id_path}")
async def get_workspace_deletion(
    workspace_id: UUID,
    request_id_path: UUID,
    request: Request,
    caller_sub: str = CALLER,
) -> dict[str, object]:
    """Polling endpoint for a single DSR (studio's "Privacy" tab)."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=None,
    )
    try:
        req = cp.data_deletion_store.get(request_id_path)
    except DataDeletionError as exc:
        raise HTTPException(status_code=404, detail="not found") from exc
    if req.workspace_id != workspace_id:
        # Tenant-isolation guard.
        raise HTTPException(status_code=404, detail="not found")
    return _serialise(req)


__all__ = ["router"]
