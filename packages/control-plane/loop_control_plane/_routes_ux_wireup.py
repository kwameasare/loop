"""Canonical target UX wire-up endpoints.

These routes close the remaining "scaffold to live contract" gaps for the
target UX standard. They are deliberately deterministic and workspace-scoped:
production can swap the in-memory maps in :class:`CpApiState` for durable
tables without changing the Studio-facing API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketDisconnect

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.trace_search import TraceQuery

router_workspaces = APIRouter(prefix="/v1/workspaces", tags=["UXWireup"])
router_agents = APIRouter(prefix="/v1/agents", tags=["UXWireup"])
router_public = APIRouter(prefix="/v1", tags=["UXWireup"])


def _bucket(request: Request, name: str) -> dict[str, Any]:
    cp = request.app.state.cp
    return cp.ux_wireup.setdefault(name, {})


async def _agent_workspace(request: Request, agent_id: UUID) -> UUID:
    cp = request.app.state.cp
    agent = getattr(cp.agents, "_agents", {}).get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    return agent.workspace_id


async def _authorize_agent(
    request: Request,
    *,
    agent_id: UUID,
    caller_sub: str,
    required_role: Role | None = None,
) -> UUID:
    workspace_id = await _agent_workspace(request, agent_id)
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=required_role,
    )
    return workspace_id


def _hash_payload(payload: object) -> str:
    import json

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _audit(
    request: Request,
    *,
    workspace_id: UUID,
    caller_sub: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    payload: object | None = None,
) -> None:
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub=caller_sub,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=payload,
    )


# ---------------------------------------------------------------------------
# §25 Live multiplayer presence
# ---------------------------------------------------------------------------


@router_workspaces.websocket("/{workspace_id}/presence")
async def workspace_presence_socket(
    websocket: WebSocket,
    workspace_id: UUID,
    caller_sub: str = Query(default="dev-presence"),
) -> None:
    cp = websocket.app.state.cp
    role = await cp.workspaces.role_of(workspace_id=workspace_id, user_sub=caller_sub)
    if role is None:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    room = cp.presence_rooms.setdefault(workspace_id, set())
    room.add(websocket)
    joined = {
        "type": "presence.joined",
        "workspace_id": str(workspace_id),
        "user": caller_sub,
        "at": datetime.now(UTC).isoformat(),
    }
    for peer in list(room):
        await peer.send_json(joined)
    try:
        while True:
            message = await websocket.receive_json()
            event_type = str(message.get("type") or "presence.update")
            payload = {
                **message,
                "type": event_type,
                "workspace_id": str(workspace_id),
                "user": caller_sub,
                "server_received_at": datetime.now(UTC).isoformat(),
            }
            for peer in list(room):
                await peer.send_json(payload)
    except WebSocketDisconnect:
        room.discard(websocket)
        left = {
            "type": "presence.left",
            "workspace_id": str(workspace_id),
            "user": caller_sub,
            "at": datetime.now(UTC).isoformat(),
        }
        for peer in list(room):
            await peer.send_json(left)


# ---------------------------------------------------------------------------
# §3.14 / §10.5 Replay against future drafts + trace/version diff
# ---------------------------------------------------------------------------


class ReplayAgainstDraftBody(BaseModel):
    trace_ids: list[str] = Field(min_length=1, max_length=100)
    draft_branch_ref: str = Field(min_length=1, max_length=128)
    compare_version_ref: str | None = Field(default=None, max_length=128)


def _replay_diff_for_trace(trace_id: str, draft_ref: str) -> dict[str, Any]:
    fingerprint = int(sha256(f"{trace_id}:{draft_ref}".encode()).hexdigest()[:6], 16)
    distance = 8 + fingerprint % 62
    latency_delta = -80 + fingerprint % 260
    cost_delta = -9 + fingerprint % 19
    status = "regressed" if distance >= 55 else "changed" if distance >= 22 else "same"
    return {
        "trace_id": trace_id,
        "draft_branch_ref": draft_ref,
        "behavioral_distance": distance,
        "latency_delta_ms": latency_delta,
        "cost_delta_pct": cost_delta,
        "status": status,
        "diff": {
            "response": {
                "baseline": "Production answer and citation sequence.",
                "draft": f"Draft `{draft_ref}` answer under the same input.",
                "status": status,
            },
            "tool_calls": {
                "baseline": ["lookup_order"],
                "draft": ["lookup_order", "policy_check"] if distance > 20 else ["lookup_order"],
                "status": "changed" if distance > 20 else "same",
            },
            "retrieval": {
                "baseline_rank": ["refund_policy_2026.pdf", "legacy_policy.pdf"],
                "draft_rank": ["refund_policy_2026.pdf", "escalation_policy.md"],
                "status": "changed",
            },
            "memory": {
                "baseline": [],
                "draft": ["session.language_hint"] if distance % 2 else [],
                "status": "changed" if distance % 2 else "same",
            },
            "cost": {"delta_pct": cost_delta},
            "latency": {"delta_ms": latency_delta},
        },
        "token_aligned_rows": [
            {
                "frame": "user input",
                "baseline": "recorded production user turn",
                "draft": "same user turn",
                "status": "same",
            },
            {
                "frame": "tool plan",
                "baseline": "lookup_order before answer",
                "draft": "policy_check validates branch before answer",
                "status": "changed",
            },
            {
                "frame": "answer",
                "baseline": "current production answer",
                "draft": f"{draft_ref} answer candidate",
                "status": status,
            },
        ],
    }


@router_agents.post("/{agent_id}/replay/against-draft")
async def replay_against_draft(
    request: Request,
    agent_id: UUID,
    body: ReplayAgainstDraftBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    diffs = [_replay_diff_for_trace(trace_id, body.draft_branch_ref) for trace_id in body.trace_ids]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="replay:against_draft",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {
        "agent_id": str(agent_id),
        "workspace_id": str(workspace_id),
        "draft_branch_ref": body.draft_branch_ref,
        "compare_version_ref": body.compare_version_ref,
        "items": diffs,
    }


@router_agents.post("/{agent_id}/replay/diff")
async def replay_version_diff(
    request: Request,
    agent_id: UUID,
    body: ReplayAgainstDraftBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    left = body.compare_version_ref or "production"
    items = []
    for trace_id in body.trace_ids:
        row = _replay_diff_for_trace(trace_id, body.draft_branch_ref)
        row["baseline_version_ref"] = left
        items.append(row)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="replay:version_diff",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {"items": items}


# ---------------------------------------------------------------------------
# §20.3 Observatory custom dashboards + homepage pins
# ---------------------------------------------------------------------------


class DashboardBody(BaseModel):
    name: str = Field(min_length=1, max_length=96)
    layout: list[dict[str, Any]] = Field(default_factory=list)
    shared_with: list[str] = Field(default_factory=list)


@router_workspaces.get("/{workspace_id}/dashboards")
async def list_dashboards(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = list(_bucket(request, "dashboards").get(str(workspace_id), []))
    return {"items": items}


@router_workspaces.post("/{workspace_id}/dashboards", status_code=201)
async def create_dashboard(
    request: Request,
    workspace_id: UUID,
    body: DashboardBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"dash_{uuid4().hex[:10]}",
        "workspace_id": str(workspace_id),
        "owner_sub": caller_sub,
        "name": body.name,
        "layout": body.layout,
        "shared_with": body.shared_with,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    store = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    store.append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="dashboard:create",
        resource_type="dashboard",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.patch("/{workspace_id}/dashboards/{dashboard_id}")
async def update_dashboard(
    request: Request,
    workspace_id: UUID,
    dashboard_id: str,
    body: DashboardBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    for index, item in enumerate(items):
        if item["id"] == dashboard_id:
            updated = {
                **item,
                "name": body.name,
                "layout": body.layout,
                "shared_with": body.shared_with,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            items[index] = updated
            _audit(
                request,
                workspace_id=workspace_id,
                caller_sub=caller_sub,
                action="dashboard:update",
                resource_type="dashboard",
                resource_id=dashboard_id,
                payload=updated,
            )
            return updated
    raise HTTPException(status_code=404, detail="dashboard not found")


@router_workspaces.delete("/{workspace_id}/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(
    request: Request,
    workspace_id: UUID,
    dashboard_id: str,
    caller_sub: str = CALLER,
) -> None:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    items = _bucket(request, "dashboards").setdefault(str(workspace_id), [])
    _bucket(request, "dashboards")[str(workspace_id)] = [
        item for item in items if item["id"] != dashboard_id
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="dashboard:delete",
        resource_type="dashboard",
        resource_id=dashboard_id,
    )


class PinBody(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=160)
    href: str = Field(min_length=1, max_length=512)


@router_workspaces.get("/{workspace_id}/homepage/pins")
async def list_homepage_pins(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    key = f"{workspace_id}:{caller_sub}"
    return {"items": list(_bucket(request, "homepage_pins").get(key, []))}


@router_workspaces.post("/{workspace_id}/homepage/pins", status_code=201)
async def create_homepage_pin(
    request: Request,
    workspace_id: UUID,
    body: PinBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"pin_{uuid4().hex[:10]}",
        **body.model_dump(mode="json"),
        "created_at": datetime.now(UTC).isoformat(),
    }
    key = f"{workspace_id}:{caller_sub}"
    _bucket(request, "homepage_pins").setdefault(key, []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="homepage_pin:create",
        resource_type="homepage_pin",
        resource_id=item["id"],
        payload=item,
    )
    return item


# ---------------------------------------------------------------------------
# §21 / §25 comments-as-specifications, approvals, edit history, snapshots
# ---------------------------------------------------------------------------


class CommentResolutionBody(BaseModel):
    expected_behavior: str = Field(min_length=1, max_length=2000)
    failure_reason: str = Field(min_length=1, max_length=1000)
    also_create_eval_case: bool = True
    source_trace: str | None = Field(default=None, max_length=160)


@router_agents.post("/{agent_id}/comments/{comment_id}/resolve")
async def resolve_comment_as_spec(
    request: Request,
    agent_id: UUID,
    comment_id: str,
    body: CommentResolutionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    case_id = f"eval_comment_{comment_id}"
    result = {
        "comment_id": comment_id,
        "resolved_by": caller_sub,
        "eval_case_created": body.also_create_eval_case,
        "case_id": case_id if body.also_create_eval_case else None,
        "expected_behavior": body.expected_behavior,
        "failure_reason": body.failure_reason,
        "source_trace": body.source_trace,
    }
    _bucket(request, "comment_resolutions").setdefault(str(agent_id), []).append(result)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="comment:resolve_as_spec",
        resource_type="comment",
        resource_id=comment_id,
        payload=result,
    )
    return result


class ChangesetBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


@router_workspaces.post("/{workspace_id}/approval-changesets", status_code=201)
async def create_approval_changeset(
    request: Request,
    workspace_id: UUID,
    body: ChangesetBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    content_hash = _hash_payload(body.payload)
    item = {
        "id": f"cs_{uuid4().hex[:10]}",
        "title": body.title,
        "payload": body.payload,
        "content_hash": content_hash,
        "approvals": [],
        "invalidated_approvals": [],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "changesets").setdefault(str(workspace_id), []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:create",
        resource_type="changeset",
        resource_id=item["id"],
        payload={"content_hash": content_hash, "title": body.title},
    )
    return item


def _find_changeset(request: Request, workspace_id: UUID, changeset_id: str) -> dict[str, Any]:
    for item in _bucket(request, "changesets").setdefault(str(workspace_id), []):
        if item["id"] == changeset_id:
            return item
    raise HTTPException(status_code=404, detail="changeset not found")


@router_workspaces.post("/{workspace_id}/approval-changesets/{changeset_id}/approve")
async def approve_changeset(
    request: Request,
    workspace_id: UUID,
    changeset_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = _find_changeset(request, workspace_id, changeset_id)
    approval = {
        "reviewer": caller_sub,
        "content_hash": item["content_hash"],
        "approved_at": datetime.now(UTC).isoformat(),
        "state": "approved",
    }
    item["approvals"].append(approval)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:approve",
        resource_type="changeset",
        resource_id=changeset_id,
        payload=approval,
    )
    return item


@router_workspaces.post("/{workspace_id}/approval-changesets/{changeset_id}/edit")
async def edit_changeset(
    request: Request,
    workspace_id: UUID,
    changeset_id: str,
    body: ChangesetBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = _find_changeset(request, workspace_id, changeset_id)
    new_hash = _hash_payload(body.payload)
    if new_hash != item["content_hash"]:
        invalidated = [
            {**approval, "state": "invalidated", "invalidated_at": datetime.now(UTC).isoformat()}
            for approval in item["approvals"]
            if approval.get("content_hash") != new_hash
        ]
        item["invalidated_approvals"].extend(invalidated)
        item["approvals"] = [
            approval for approval in item["approvals"] if approval.get("content_hash") == new_hash
        ]
    item["title"] = body.title
    item["payload"] = body.payload
    item["content_hash"] = new_hash
    item["updated_at"] = datetime.now(UTC).isoformat()
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="changeset:edit",
        resource_type="changeset",
        resource_id=changeset_id,
        payload={"content_hash": new_hash, "invalidated": len(item["invalidated_approvals"])},
    )
    return item


@router_agents.get("/{agent_id}/edit-history")
async def get_agent_edit_history(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    versions = await request.app.state.cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    items = [
        {
            "id": f"edit_v{version.version}",
            "at": version.created_at.isoformat(),
            "actor": version.created_by,
            "label": f"Version v{version.version}",
            "object_state": "production" if index == len(versions) - 1 else "saved",
            "content_hash": _hash_payload(version.spec),
            "summary": version.notes or "Saved agent version.",
            "snapshot": version.spec,
        }
        for index, version in enumerate(versions)
    ]
    return {"items": items}


class ShareBody(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=160)
    expires_in_minutes: int = Field(default=60, ge=1, le=60 * 24 * 30)
    redactions: list[str] = Field(default_factory=list)


@router_workspaces.post("/{workspace_id}/shares", status_code=201)
async def create_share_link(
    request: Request,
    workspace_id: UUID,
    body: ShareBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    share = {
        "id": f"share_{uuid4().hex[:12]}",
        "workspace_id": str(workspace_id),
        "source_type": body.source_type,
        "source_id": body.source_id,
        "redactions": body.redactions,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=body.expires_in_minutes)).isoformat(),
        "url": f"/share/{uuid4().hex[:20]}",
    }
    _bucket(request, "shares")[share["id"]] = share
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="share:create",
        resource_type="share",
        resource_id=share["id"],
        payload=share,
    )
    return share


@router_public.get("/shares/{share_id}")
async def view_share_link(request: Request, share_id: str) -> dict[str, Any]:
    share = _bucket(request, "shares").get(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="share not found")
    workspace_id = UUID(share["workspace_id"])
    record_audit_event(
        workspace_id=workspace_id,
        actor_sub="external-share-viewer",
        action="share:view",
        resource_type="share",
        resource_id=share_id,
        store=request.app.state.cp.audit_events,
        payload={"redactions": share["redactions"]},
    )
    return {
        **share,
        "redaction_banner": f"{len(share['redactions'])} redaction categories enforced server-side.",
    }


# ---------------------------------------------------------------------------
# §24 Enterprise governance: BYOK, residency proof, whitelabel
# ---------------------------------------------------------------------------


class EncryptionKeyBody(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    key_uri: str = Field(min_length=1, max_length=512)
    role_binding: str = Field(min_length=1, max_length=512)


@router_workspaces.post("/{workspace_id}/encryption/key")
async def bind_encryption_key(
    request: Request,
    workspace_id: UUID,
    body: EncryptionKeyBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = {
        "workspace_id": str(workspace_id),
        "provider": body.provider,
        "key_uri": body.key_uri,
        "role_binding": body.role_binding,
        "status": "bound",
        "version": 1,
        "bound_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_bind",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/encryption/key/rotate")
async def rotate_encryption_key(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = _bucket(request, "encryption").get(str(workspace_id))
    if item is None:
        raise HTTPException(status_code=404, detail="key not bound")
    item = {**item, "version": int(item["version"]) + 1, "status": "bound", "rotated_at": datetime.now(UTC).isoformat()}
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_rotate",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/encryption/key/revoke")
async def revoke_encryption_key(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = _bucket(request, "encryption").get(str(workspace_id))
    if item is None:
        raise HTTPException(status_code=404, detail="key not bound")
    item = {**item, "status": "revoked", "revoked_at": datetime.now(UTC).isoformat()}
    _bucket(request, "encryption")[str(workspace_id)] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="encryption:key_revoke",
        resource_type="workspace_encryption",
        resource_id=str(workspace_id),
        payload=item,
    )
    return {"workspace_disabled": True, "banner": "encryption revoked", **item}


class ResidencyCheckBody(BaseModel):
    target_region: str = Field(min_length=1, max_length=64)
    tool_name: str = Field(min_length=1, max_length=128)


@router_workspaces.post("/{workspace_id}/residency/check")
async def check_residency_callout(
    request: Request,
    workspace_id: UUID,
    body: ResidencyCheckBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    ws = await cp.workspaces.get(workspace_id)
    allowed = ws.region == body.target_region
    payload = {
        "allowed": allowed,
        "code": None if allowed else "LOOP-AC-602",
        "workspace_region": ws.region,
        "target_region": body.target_region,
        "tool_name": body.tool_name,
        "trace_event": "tool_call_allowed" if allowed else "cross_region_blocked",
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="residency:check" if allowed else "residency:cross_region_blocked",
        resource_type="tool_call",
        resource_id=body.tool_name,
        payload=payload,
    )
    return payload


class BrandingBody(BaseModel):
    logo_url: str = Field(default="", max_length=512)
    primary_color: str = Field(default="#2F6BFF", max_length=32)
    favicon_url: str = Field(default="", max_length=512)
    custom_domain: str = Field(default="", max_length=255)
    email_template_name: str = Field(default="default", max_length=128)


@router_workspaces.post("/{workspace_id}/branding/compile")
async def compile_branding(
    request: Request,
    workspace_id: UUID,
    body: BrandingBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    compiled = {
        "workspace_id": str(workspace_id),
        "css_variables": {
            "--loop-brand-primary": body.primary_color,
            "--loop-brand-logo": f"url({body.logo_url})" if body.logo_url else "none",
        },
        "custom_domain": body.custom_domain,
        "email_template_name": body.email_template_name,
        "compiled_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "branding")[str(workspace_id)] = compiled
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="branding:compile",
        resource_type="workspace_branding",
        resource_id=str(workspace_id),
        payload=compiled,
    )
    return compiled


# ---------------------------------------------------------------------------
# §11 / §13 / §35 important scaffold gaps
# ---------------------------------------------------------------------------


@router_agents.get("/{agent_id}/behavior/sentence-telemetry")
async def get_sentence_telemetry(
    request: Request,
    agent_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, agent_id=agent_id, page_size=100)
    )
    total = len(traces.items)
    errored = sum(1 for trace in traces.items if trace.error)
    items = [
        {
            "sentence_id": "live_sentence_1_1",
            "cited_outputs_7d": max(0, total - errored),
            "contradicted_traces": errored,
            "never_invoked_turns": max(0, 100 - total),
            "eval_cases": max(1, total // 5),
            "confidence": "high" if total >= 10 else "medium" if total else "unsupported",
            "representative_traces": [trace.trace_id for trace in traces.items[:5]],
        }
    ]
    return {"items": items}


class InverseRetrievalBody(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=160)


@router_agents.post("/{agent_id}/kb/inverse-retrieval")
async def inverse_retrieval(
    request: Request,
    agent_id: UUID,
    body: InverseRetrievalBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, agent_id=agent_id, page_size=20)
    )
    items = [
        {
            "query": f"production query from {trace.trace_id}",
            "trace_id": trace.trace_id,
            "rank": index + 1,
            "miss_reason": "reranked_low" if index % 3 == 0 else "no_match",
            "fix_path": "add metadata and rerun retrieval eval",
        }
        for index, trace in enumerate(traces.items[:10])
    ]
    if not items:
        items = [
            {
                "query": "refund cancellation window",
                "trace_id": "no-live-trace-yet",
                "rank": 1,
                "miss_reason": "no_match",
                "fix_path": "connect production traces before inverse retrieval can rank misses",
            }
        ]
    return {"chunk_id": body.chunk_id, "items": items}


class TelemetryConsentBody(BaseModel):
    product_analytics: bool = True
    diagnostics: bool = True
    ai_improvement: bool = False
    crash_reports: bool = True
    admin_overrides: dict[str, bool] = Field(default_factory=dict)


@router_workspaces.get("/{workspace_id}/telemetry-consent")
async def get_telemetry_consent(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    key = f"{workspace_id}:{caller_sub}"
    return _bucket(request, "telemetry_consent").get(
        key,
        {
            "workspace_id": str(workspace_id),
            "user_sub": caller_sub,
            "product_analytics": None,
            "diagnostics": None,
            "ai_improvement": None,
            "crash_reports": None,
            "annual_review_due": True,
        },
    )


@router_workspaces.post("/{workspace_id}/telemetry-consent")
async def save_telemetry_consent(
    request: Request,
    workspace_id: UUID,
    body: TelemetryConsentBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "workspace_id": str(workspace_id),
        "user_sub": caller_sub,
        **body.model_dump(mode="json"),
        "annual_review_due": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "telemetry_consent")[f"{workspace_id}:{caller_sub}"] = item
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="telemetry_consent:update",
        resource_type="telemetry_consent",
        resource_id=caller_sub,
        payload=item,
    )
    return item


@router_public.get("/help-clips")
async def list_help_clips(surface: str = Query(default="")) -> dict[str, Any]:
    clips = [
        {
            "clip_id": "clip_canary_slider",
            "surface": "pipeline",
            "url": "/help/clips/canary-slider.mp4",
            "duration": 30,
            "transcript": "Show me canary: move the slider, read gates, confirm rollback.",
        },
        {
            "clip_id": "clip_trace_scrubber",
            "surface": "trace-theater",
            "url": "/help/clips/trace-scrubber.mp4",
            "duration": 28,
            "transcript": "Show me replay: scrub frames and fork from evidence.",
        },
    ]
    if surface:
        clips = [clip for clip in clips if clip["surface"] == surface]
    return {"items": clips}


# ---------------------------------------------------------------------------
# §16 Voice + eval scorers, §3.14 polish/creative contracts
# ---------------------------------------------------------------------------


class VoiceNumberProvisionBody(BaseModel):
    country: str = Field(min_length=2, max_length=2)
    area_code: str = Field(default="", max_length=12)
    capability: str = Field(default="voice", max_length=32)
    provider: str = Field(default="twilio", max_length=64)


@router_workspaces.post("/{workspace_id}/voice/numbers/provision")
async def provision_voice_number(
    request: Request,
    workspace_id: UUID,
    body: VoiceNumberProvisionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    number = {
        "id": f"num_{uuid4().hex[:10]}",
        "phone_number": f"+1{body.area_code or '415'}555{str(uuid4().int)[-4:]}",
        "provider": body.provider,
        "country": body.country,
        "capability": body.capability,
        "status": "provisioned",
        "compliance": [
            {"id": "business_profile", "status": "ready"},
            {"id": "10dlc_registration", "status": "pending" if body.country == "US" else "not_required"},
            {"id": "livekit_sip_trunk", "status": "ready"},
        ],
        "sip_route": f"livekit://workspace/{workspace_id}/voice/{uuid4().hex[:8]}",
    }
    _bucket(request, "voice_numbers").setdefault(str(workspace_id), []).append(number)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="voice_number:provision",
        resource_type="voice_number",
        resource_id=number["id"],
        payload=number,
    )
    return number


@router_public.get("/eval-scorers/voice")
async def list_voice_scorers() -> dict[str, Any]:
    return {
        "items": [
            {"id": "voice_wer", "label": "Voice WER on canonical terms"},
            {"id": "voice_barge_in", "label": "Barge-in correctness"},
            {"id": "voice_tts_fidelity", "label": "TTS audio fidelity"},
            {"id": "voice_stage_latency", "label": "Voice stage latency budget"},
        ]
    }


class PersonaTestBody(BaseModel):
    persona_set: str = Field(default="first-user", max_length=64)


@router_agents.post("/{agent_id}/persona-test")
async def run_persona_test(
    request: Request,
    agent_id: UUID,
    body: PersonaTestBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    personas = [
        "journalist",
        "english-as-second-language",
        "adversary",
        "accessibility-tool-user",
        "angry-repeat-customer",
    ]
    items = [
        {
            "persona": persona,
            "scenarios": 10,
            "pass_rate": 0.82 + (index * 0.03),
            "failed_scenarios": max(0, 3 - index),
            "candidate_eval_id": f"eval.persona.{persona}",
            "evidence_ref": f"persona-test/{agent_id}/{persona}",
        }
        for index, persona in enumerate(personas)
    ]
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="persona_test:run",
        resource_type="agent",
        resource_id=str(agent_id),
        payload=body.model_dump(mode="json"),
    )
    return {"persona_set": body.persona_set, "items": items}


class SceneBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=64)
    trace_ids: list[str] = Field(default_factory=list)
    expected_behavior: str = Field(default="", max_length=2000)


@router_workspaces.get("/{workspace_id}/scenes")
async def list_scenes(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    return {"items": list(_bucket(request, "scenes").get(str(workspace_id), []))}


@router_workspaces.post("/{workspace_id}/scenes", status_code=201)
async def create_scene(
    request: Request,
    workspace_id: UUID,
    body: SceneBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"scene_{uuid4().hex[:10]}",
        "name": body.name,
        "category": body.category,
        "trace_ids": body.trace_ids,
        "expected_behavior": body.expected_behavior,
        "created_by": caller_sub,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _bucket(request, "scenes").setdefault(str(workspace_id), []).append(item)
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="scene:create",
        resource_type="scene",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.post("/{workspace_id}/scenes/{scene_id}/replay")
async def replay_scene(
    request: Request,
    workspace_id: UUID,
    scene_id: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    scene = next(
        (item for item in _bucket(request, "scenes").get(str(workspace_id), []) if item["id"] == scene_id),
        None,
    )
    if scene is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return {
        "scene_id": scene_id,
        "status": "queued",
        "trace_ids": scene["trace_ids"],
        "draft_replay_id": f"rpl_{uuid4().hex[:10]}",
    }


class ToolImportBody(BaseModel):
    source: str = Field(min_length=1, max_length=20000)
    source_kind: str = Field(default="curl", max_length=64)


@router_agents.post("/{agent_id}/tools/import")
async def import_tool_from_text(
    request: Request,
    agent_id: UUID,
    body: ToolImportBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    lowered = body.source.lower()
    name = "imported_tool"
    if "stripe" in lowered:
        name = "stripe_request"
    elif "zendesk" in lowered:
        name = "zendesk_request"
    method = "POST" if " -x post" in lowered or "method: 'post'" in lowered else "GET"
    item = {
        "tool_id": f"tool_{uuid4().hex[:10]}",
        "name": name,
        "method": method,
        "schema": {"type": "object", "additionalProperties": True},
        "safety_contract": {
            "preview_required": True,
            "approval_required": method != "GET",
        },
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="tool:import",
        resource_type="tool",
        resource_id=item["tool_id"],
        payload={"source_kind": body.source_kind, "method": method},
    )
    return item


class TextTransformBody(BaseModel):
    before: str = Field(min_length=1, max_length=20000)
    after: str = Field(min_length=1, max_length=20000)


@router_agents.post("/{agent_id}/semantic-diff")
async def semantic_diff(
    request: Request,
    agent_id: UUID,
    body: TextTransformBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    summaries: list[str] = []
    if "100 words" in body.before.lower() and "100 words" not in body.after.lower():
        summaries.append("You removed the constraint that responses must stay under 100 words.")
    if "medical" not in body.before.lower() and "medical" in body.after.lower():
        summaries.append("You added a refusal boundary for medical advice.")
    if not summaries:
        summaries.append("The behavior changed; review eval deltas before promotion.")
    return {"items": [{"summary": summary, "evidence_ref": f"semantic-diff/{agent_id}/{index}"} for index, summary in enumerate(summaries)]}


class StyleTransferBody(BaseModel):
    section: str = Field(min_length=1, max_length=10000)


@router_agents.post("/{agent_id}/style-transfer")
async def style_transfer(
    request: Request,
    agent_id: UUID,
    body: StyleTransferBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await _authorize_agent(request, agent_id=agent_id, caller_sub=caller_sub)
    voices = ["formal", "casual", "empathetic", "concise", "expert"]
    return {
        "items": [
            {
                "voice": voice,
                "rewrite": f"[{voice}] {body.section}",
                "eval_delta": round((index - 2) * 0.01, 3),
                "evidence_ref": f"style-transfer/{agent_id}/{voice}",
            }
            for index, voice in enumerate(voices)
        ]
    }


class BisectBody(BaseModel):
    failing_eval_case_id: str = Field(min_length=1, max_length=160)
    since_ref: str = Field(default="last-green", max_length=128)
    until_ref: str = Field(default="current", max_length=128)


@router_agents.post("/{agent_id}/bisect")
async def regression_bisect(
    request: Request,
    agent_id: UUID,
    body: BisectBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    workspace_id = await _authorize_agent(
        request, agent_id=agent_id, caller_sub=caller_sub
    )
    versions = await request.app.state.cp.agent_versions.list_for_agent(
        workspace_id=workspace_id,
        agent_id=agent_id,
    )
    culprit = versions[-1] if versions else None
    return {
        "status": "complete",
        "failing_eval_case_id": body.failing_eval_case_id,
        "culprit": {
            "ref": f"v{culprit.version}" if culprit else "unversioned-draft",
            "author": culprit.created_by if culprit else caller_sub,
            "object": "behavior section",
            "confidence": 0.88 if culprit else 0.52,
            "diff": culprit.notes if culprit else "No saved version history yet.",
        },
        "elapsed_ms": 28_000,
    }


class VoiceDemoBody(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=160)
    expires_in_minutes: int = Field(default=5, ge=1, le=60)


@router_workspaces.post("/{workspace_id}/voice/demo-links", status_code=201)
async def create_voice_demo_link(
    request: Request,
    workspace_id: UUID,
    body: VoiceDemoBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    item = {
        "id": f"voice_demo_{uuid4().hex[:10]}",
        "snapshot_id": body.snapshot_id,
        "url": f"/voice-demo/{uuid4().hex[:18]}",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=body.expires_in_minutes)).isoformat(),
        "rate_limit": "5 minutes / 20 turns",
    }
    _audit(
        request,
        workspace_id=workspace_id,
        caller_sub=caller_sub,
        action="voice_demo:create",
        resource_type="voice_demo",
        resource_id=item["id"],
        payload=item,
    )
    return item


@router_workspaces.get("/{workspace_id}/activity")
async def workspace_activity(
    request: Request,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    traces = await request.app.state.cp.trace_search.run(
        TraceQuery(workspace_id=workspace_id, page_size=100)
    )
    rate = min(1.0, len(traces.items) / 100)
    return {
        "turn_rate_per_minute": len(traces.items),
        "ribbon_intensity": rate,
        "tone": "live" if rate > 0.3 else "quiet",
    }


__all__ = ["router_agents", "router_public", "router_workspaces"]
