"""Marketplace browse routes for Studio."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from loop_control_plane._app_common import CALLER, request_id
from loop_control_plane.audit_events import record_audit_event
from loop_control_plane.authorize import Role, authorize_workspace_access
from loop_control_plane.mcp_marketplace import MarketplaceBrowser

router = APIRouter(prefix="/v1/marketplace", tags=["Marketplace"])


@router.get("")
async def browse_marketplace(
    request: Request,
    q: str = Query(default=""),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    # ``caller_sub`` ensures the auth dependency runs even though the first-party
    # catalog itself is workspace-neutral.
    _ = caller_sub
    browser = MarketplaceBrowser(store=request.app.state.cp.marketplace_store)
    items = browser.browse(query=q, category=category, limit=limit)
    private_items = list(request.app.state.cp.ux_wireup.setdefault("marketplace_items", {}).values())
    rows = [item.model_dump(mode="json") for item in items]
    if q:
        q_lower = q.lower()
        private_items = [
            item
            for item in private_items
            if q_lower in item["name"].lower() or q_lower in item["slug"].lower()
        ]
    rows.extend(private_items[: max(0, limit - len(rows))])
    return {"items": rows}


class MarketplacePublishBody(BaseModel):
    workspace_id: UUID
    slug: str = Field(min_length=1, max_length=96, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    categories: list[str] = Field(default_factory=list)
    version: str = Field(default="0.1.0", pattern=r"^\d+\.\d+\.\d+$")
    permissions: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)


def _cp_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["server_id"],
        "server_id": item["server_id"],
        "slug": item["slug"],
        "name": item["name"],
        "publisher": item["publisher"],
        "description": item["description"],
        "categories": item["categories"],
        "latest_version": item["latest_version"],
        "quality_score": item["quality_score"],
        "average_rating": item["average_rating"],
        "installs": item["installs"],
        "calls": item["calls"],
        "install_button_enabled": item["install_button_enabled"],
        "lifecycle": item["lifecycle"],
        "versions": item["versions"],
        "deprecation_notice": item.get("deprecation_notice"),
    }


@router.post("/items", status_code=201)
async def publish_marketplace_item(
    request: Request,
    body: MarketplacePublishBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=body.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    sensitive = {"money-movement", "write-secrets", "deploy-production"}
    if sensitive.intersection(body.permissions) and len(body.reviewers) < 2:
        raise HTTPException(status_code=400, detail="sensitive permissions require two reviewers")
    item = {
        "server_id": f"mk_private_{uuid4().hex[:10]}",
        "workspace_id": str(body.workspace_id),
        "slug": body.slug,
        "name": body.name,
        "publisher": f"workspace:{body.workspace_id}",
        "description": body.description,
        "categories": body.categories or ["private", "skill"],
        "latest_version": body.version,
        "quality_score": 82,
        "average_rating": 0,
        "installs": 0,
        "calls": 0,
        "install_button_enabled": True,
        "lifecycle": "published",
        "permissions": body.permissions,
        "reviewers": body.reviewers,
        "versions": [
            {
                "version": body.version,
                "released_at": datetime.now(UTC).isoformat(),
                "changelog": "Initial private skill publication.",
                "signed": False,
            }
        ],
    }
    request.app.state.cp.ux_wireup.setdefault("marketplace_items", {})[item["server_id"]] = item
    record_audit_event(
        workspace_id=body.workspace_id,
        actor_sub=caller_sub,
        action="marketplace:item_publish",
        resource_type="marketplace_item",
        resource_id=item["server_id"],
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=item,
    )
    return _cp_item(item)


class MarketplaceVersionBody(BaseModel):
    workspace_id: UUID
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    changelog: str = Field(min_length=1, max_length=2000)


@router.post("/items/{item_id}/versions", status_code=201)
async def publish_marketplace_version(
    request: Request,
    item_id: str,
    body: MarketplaceVersionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=body.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = request.app.state.cp.ux_wireup.setdefault("marketplace_items", {}).get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="marketplace item not found")
    version = {
        "version": body.version,
        "released_at": datetime.now(UTC).isoformat(),
        "changelog": body.changelog,
        "signed": False,
    }
    item["latest_version"] = body.version
    item["versions"].insert(0, version)
    record_audit_event(
        workspace_id=body.workspace_id,
        actor_sub=caller_sub,
        action="marketplace:item_version",
        resource_type="marketplace_item",
        resource_id=item_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=version,
    )
    return _cp_item(item)


class MarketplaceActionBody(BaseModel):
    workspace_id: UUID
    reason: str = Field(default="", max_length=1000)


@router.post("/items/{item_id}/deprecate")
async def deprecate_marketplace_item(
    request: Request,
    item_id: str,
    body: MarketplaceActionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=body.workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    item = request.app.state.cp.ux_wireup.setdefault("marketplace_items", {}).get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="marketplace item not found")
    item["lifecycle"] = "deprecated"
    item["deprecation_notice"] = body.reason or "Deprecated by workspace administrator."
    record_audit_event(
        workspace_id=body.workspace_id,
        actor_sub=caller_sub,
        action="marketplace:item_deprecate",
        resource_type="marketplace_item",
        resource_id=item_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload={"reason": item["deprecation_notice"]},
    )
    return _cp_item(item)


@router.post("/items/{item_id}/install", status_code=201)
async def install_marketplace_item(
    request: Request,
    item_id: str,
    body: MarketplaceActionBody,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=body.workspace_id,
        user_sub=caller_sub,
    )
    item = request.app.state.cp.ux_wireup.setdefault("marketplace_items", {}).get(item_id)
    if item is None:
        # First-party MCP catalog item IDs are accepted too; install audit is
        # the important enterprise trail even when the item lives in the
        # immutable first-party store.
        item = {"server_id": item_id, "latest_version": "catalog"}
    install = {
        "install_id": f"inst_{uuid4().hex[:10]}",
        "item_id": item_id,
        "workspace_id": str(body.workspace_id),
        "version": item.get("latest_version", "unknown"),
        "installed_by": caller_sub,
        "installed_at": datetime.now(UTC).isoformat(),
        "audit_ref": f"marketplace.install.{item_id}",
    }
    request.app.state.cp.ux_wireup.setdefault("marketplace_installs", {}).setdefault(item_id, []).append(install)
    if "installs" in item:
        item["installs"] += 1
    record_audit_event(
        workspace_id=body.workspace_id,
        actor_sub=caller_sub,
        action="marketplace:item_install",
        resource_type="marketplace_item",
        resource_id=item_id,
        store=request.app.state.cp.audit_events,
        request_id=request_id(request),
        payload=install,
    )
    return install


@router.get("/items/{item_id}/installs")
async def list_marketplace_installs(
    request: Request,
    item_id: str,
    workspace_id: UUID,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    await authorize_workspace_access(
        workspaces=request.app.state.cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
        required_role=Role.ADMIN,
    )
    installs = list(request.app.state.cp.ux_wireup.setdefault("marketplace_installs", {}).get(item_id, []))
    return {"items": installs}


__all__ = ["router"]
