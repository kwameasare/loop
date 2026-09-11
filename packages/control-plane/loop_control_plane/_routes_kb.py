"""Workspace KB document routes (P0.4).

* ``GET    /v1/workspaces/{id}/kb/documents``         (any member)
* ``POST   /v1/workspaces/{id}/kb/documents``         (ADMIN, idempotent)
* ``DELETE /v1/workspaces/{id}/kb/documents/{kid}``   (ADMIN)
* ``POST   /v1/workspaces/{id}/kb/refresh``           (ADMIN — refresh all)
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from loop_control_plane._agent_route_utils import resolve_agent_for_route
from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.kb_documents import (
    KbDocumentCreate,
    KbError,
    serialise_doc,
)

router = APIRouter(prefix="/v1/workspaces", tags=["KB"])
router_agents = APIRouter(prefix="/v1/agents", tags=["KB"])
router_global = APIRouter(prefix="/v1/kb", tags=["KB"])


class KbRefreshPatch(BaseModel):
    cadence: str = Field(default="manual", max_length=32)


async def _agent_for_id(request: Request, agent_id: UUID) -> Any:
    try:
        return await request.app.state.cp.agents.get_by_id(agent_id=agent_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="unknown agent") from exc


async def _authorise_agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> Any:
    return await resolve_agent_for_route(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=required_role,
    )


def _studio_status(state: str) -> str:
    if state == "ready":
        return "ready"
    if state == "failed":
        return "error"
    return "indexing"


def _studio_doc(agent_id: UUID, doc: Any) -> dict[str, Any]:
    return {
        "id": str(doc.id),
        "agentId": str(agent_id),
        "name": doc.title or doc.source_url,
        "contentType": doc.content_type,
        "bytes": doc.byte_size,
        "status": _studio_status(doc.state.value),
        "uploadedAt": doc.created_at.isoformat(),
        "lastRefreshedAt": (
            doc.last_refreshed_at.isoformat() if doc.last_refreshed_at else None
        ),
    }


def _refresh_status(doc: Any, cadence: str = "manual") -> dict[str, Any]:
    return {
        "documentId": str(doc.id),
        "cadence": cadence,
        "status": "running" if doc.state.value == "ingesting" else "ok",
        "lastRunAt": (
            doc.last_refreshed_at.isoformat() if doc.last_refreshed_at else None
        ),
        "nextRunAt": None,
        "runCount": 1 if doc.last_refreshed_at else 0,
        "error": doc.failure_reason,
    }


def _multipart_file_meta(body: bytes) -> tuple[str, str, int]:
    head = body[:4096].decode("utf-8", errors="ignore")
    filename_match = re.search(r'filename="([^"]*)"', head)
    content_type_match = re.search(
        r"Content-Type:\s*([^\r\n]+)",
        head,
        re.IGNORECASE,
    )
    filename = filename_match.group(1).strip() if filename_match else "uploaded-document"
    content_type = (
        content_type_match.group(1).strip()
        if content_type_match
        else "application/octet-stream"
    )
    return filename or "uploaded-document", content_type, len(body)


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


@router_agents.get("/{agent_id}/kb/documents")
async def list_agent_kb_documents(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _authorise_agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
    )
    rows = await request.app.state.cp.kb_documents.list_for_workspace(agent.workspace_id)
    return {"items": [_studio_doc(agent_id, doc) for doc in rows]}


@router_agents.post("/{agent_id}/kb/documents", status_code=201)
async def create_agent_kb_document(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    agent = await _authorise_agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("application/json"):
            payload = await request.json()
            doc = await request.app.state.cp.kb_documents.create(
                workspace_id=agent.workspace_id,
                body=KbDocumentCreate(**payload),
            )
        else:
            filename, upload_content_type, byte_size = _multipart_file_meta(
                await request.body()
            )
            doc = await request.app.state.cp.kb_documents.create_upload(
                workspace_id=agent.workspace_id,
                filename=filename,
                content_type=upload_content_type,
                byte_size=byte_size,
            )
    except (KbError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=agent.workspace_id,
        actor_sub=caller_sub,
        action="kb:document:create",
        resource_type="kb_document",
        store=request.app.state.cp.audit_events,
        resource_id=str(doc.id),
        request_id=request_id(request),
        payload={
            "agent_id": str(agent_id),
            "id": str(doc.id),
            "source_kind": doc.source_kind,
            "source_url": doc.source_url,
            "title": doc.title,
        },
    )
    return _studio_doc(agent_id, doc)


@router_agents.delete("/{agent_id}/kb/documents/{document_id}", status_code=204)
async def delete_agent_kb_document(
    request: Request,
    agent_id: UUID,
    document_id: UUID,
    caller_sub: str = CALLER,
) -> None:
    agent = await _authorise_agent(
        request,
        agent_id=agent_id,
        caller_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    try:
        await request.app.state.cp.kb_documents.delete(
            workspace_id=agent.workspace_id,
            document_id=document_id,
        )
    except KbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        workspace_id=agent.workspace_id,
        actor_sub=caller_sub,
        action="kb:document:delete",
        resource_type="kb_document",
        store=request.app.state.cp.audit_events,
        resource_id=str(document_id),
        request_id=request_id(request),
        payload={"agent_id": str(agent_id), "id": str(document_id)},
    )


@router_global.get("/documents/{document_id}/refresh")
async def get_kb_document_refresh(
    request: Request,
    document_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    try:
        doc = await request.app.state.cp.kb_documents.find(document_id=document_id)
    except KbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=doc.workspace_id,
        user_sub=caller_sub,
    )
    return _refresh_status(doc)


@router_global.patch("/documents/{document_id}/refresh")
async def patch_kb_document_refresh(
    request: Request,
    document_id: UUID,
    body: KbRefreshPatch,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    try:
        doc = await request.app.state.cp.kb_documents.find(document_id=document_id)
    except KbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=doc.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    return _refresh_status(doc, cadence=body.cadence)


@router_global.post("/documents/{document_id}/refresh")
async def trigger_kb_document_refresh(
    request: Request,
    document_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    try:
        doc = await request.app.state.cp.kb_documents.find(document_id=document_id)
    except KbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=doc.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    refreshed = await request.app.state.cp.kb_documents.refresh(
        workspace_id=doc.workspace_id,
        document_id=document_id,
    )
    record_audit_event(
        workspace_id=refreshed.workspace_id,
        actor_sub=caller_sub,
        action="kb:document:refresh",
        resource_type="kb_document",
        store=request.app.state.cp.audit_events,
        resource_id=str(document_id),
        request_id=request_id(request),
        payload={"id": str(document_id)},
    )
    return _refresh_status(refreshed)


__all__ = ["router", "router_agents", "router_global"]
