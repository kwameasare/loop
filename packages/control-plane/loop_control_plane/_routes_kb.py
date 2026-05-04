"""Workspace KB document routes (P0.4).

* ``GET    /v1/workspaces/{id}/kb/documents``         (any member)
* ``POST   /v1/workspaces/{id}/kb/documents``         (ADMIN, idempotent)
* ``DELETE /v1/workspaces/{id}/kb/documents/{kid}``   (ADMIN)
* ``POST   /v1/workspaces/{id}/kb/refresh``           (ADMIN — refresh all)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.kb_documents import (
    KbDocumentCreate,
    KbError,
    serialise_doc,
)

router = APIRouter(prefix="/v1/workspaces", tags=["KB"])


@router.get("/{workspace_id}/kb/documents")
async def list_kb_documents(
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
    rows = await cp.kb_documents.list_for_workspace(workspace_id)
    return {"items": [serialise_doc(d) for d in rows]}


@router.post("/{workspace_id}/kb/documents", status_code=201)
async def create_kb_document(
    request: Request,
    workspace_id: UUID,
    body: KbDocumentCreate,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        doc = await cp.kb_documents.create(workspace_id=workspace_id, body=body)
    except KbError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="kb:document:create",
        resource_type="kb_document",
        store=cp.audit_events,
        resource_id=str(doc.id),
        request_id=request_id(request),
        payload={"id": str(doc.id), "source_url": doc.source_url, "title": doc.title},
    )
    return serialise_doc(doc)


@router.delete("/{workspace_id}/kb/documents/{document_id}", status_code=204)
async def delete_kb_document(
    request: Request,
    workspace_id: UUID,
    document_id: UUID,
    caller_sub: str = CALLER,
) -> None:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        await cp.kb_documents.delete(
            workspace_id=workspace_id, document_id=document_id
        )
    except KbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="kb:document:delete",
        resource_type="kb_document",
        store=cp.audit_events,
        resource_id=str(document_id),
        request_id=request_id(request),
        payload={"id": str(document_id)},
    )


@router.post("/{workspace_id}/kb/refresh")
async def refresh_workspace_kb(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Trigger re-ingestion of every KB document in the workspace.
    Idempotent."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    rows = await cp.kb_documents.refresh_all(workspace_id)
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action="kb:refresh_all",
        resource_type="kb_workspace",
        store=cp.audit_events,
        resource_id=str(workspace_id),
        request_id=request_id(request),
        payload={"document_count": len(rows)},
    )
    return {
        "items": [serialise_doc(r) for r in rows],
        "refreshed_at": (
            rows[0].last_refreshed_at.isoformat() if rows and rows[0].last_refreshed_at else None
        ),
    }


__all__ = ["router"]
