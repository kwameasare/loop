"""HTTP-shaped facade over :class:`WorkspaceService` (S108-S112).

Framework-agnostic: every method takes JSON-shaped ``dict`` input
(``body``) plus typed kwargs and returns a JSON-shaped ``dict``,
mirroring the eventual REST routes:

* ``POST   /v1/workspaces``                                     -> :meth:`create`
* ``GET    /v1/workspaces``                                     -> :meth:`list_for_caller`
* ``GET    /v1/workspaces/{id}``                                -> :meth:`get`
* ``PATCH  /v1/workspaces/{id}``                                -> :meth:`patch`
* ``GET    /v1/workspaces/{id}/members``                        -> :meth:`list_members`
* ``POST   /v1/workspaces/{id}/members``                        -> :meth:`add_member`
* ``DELETE /v1/workspaces/{id}/members/{user_sub}``             -> :meth:`remove_member`
* ``PATCH  /v1/workspaces/{id}/members/{user_sub}``             -> :meth:`update_member_role`

Authorisation: every method that touches an existing workspace runs
:func:`authorize_workspace_access` first. Routes that mutate state
require the ``OWNER`` role; member listing requires bare membership.

Errors map to LOOP-API codes via :func:`map_to_loop_api_error` (S118).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from loop_control_plane.authorize import (
    AuthorisationError,
    authorize_workspace_access,
)
from loop_control_plane.data_exports import DataExportStore
from loop_control_plane.region_routing import DataPlaneTransport, RegionRouter
from loop_control_plane.regions import RegionError
from loop_control_plane.workspaces import (
    Membership,
    Role,
    Workspace,
    WorkspaceError,
    WorkspaceService,
)


def _serialise_ws(ws: Workspace) -> dict[str, Any]:
    return ws.model_dump(mode="json")


def _serialise_member(m: Membership) -> dict[str, Any]:
    return m.model_dump(mode="json")


def _require_str(name: str, value: object, *, min_length: int = 1) -> str:
    if not isinstance(value, str) or len(value) < min_length:
        raise WorkspaceError(f"{name} must be a non-empty string")
    return value


def _require_role(name: str, value: object) -> Role:
    if not isinstance(value, str):
        raise WorkspaceError(f"{name} must be a string")
    try:
        return Role(value)
    except ValueError as exc:
        raise WorkspaceError(f"{name} must be one of {[r.value for r in Role]}") from exc


@dataclass
class WorkspaceAPI:
    """Thin facade so HTTP routers stay one-liners.

    Every method that mutates an existing workspace requires the
    caller to be an OWNER. Listing members requires plain membership.
    """

    workspaces: WorkspaceService
    region_router: RegionRouter = field(default_factory=RegionRouter)

    def _require_request_region(self, *, workspace: Workspace, request_region: str | None) -> None:
        if request_region is None:
            return
        try:
            self.workspaces.require_same_region(
                workspace_region=workspace.region,
                request_region=request_region,
            )
        except RegionError as exc:
            raise AuthorisationError(str(exc)) from exc

    # -- S108 --------------------------------------------------------------- #
    async def create(self, *, caller_sub: str, body: dict[str, Any]) -> dict[str, Any]:
        """Create a workspace; the caller becomes the OWNER. Returns 201 body."""
        name = _require_str("name", body.get("name"))
        slug = _require_str("slug", body.get("slug"))
        region = body.get("region")
        if region is not None and not isinstance(region, str):
            raise WorkspaceError("region must be a string")
        tenant_kms_key_id = body.get("tenant_kms_key_id")
        if tenant_kms_key_id is not None and not isinstance(tenant_kms_key_id, str):
            raise WorkspaceError("tenant_kms_key_id must be a string")
        ws = await self.workspaces.create(
            name=name,
            slug=slug,
            owner_sub=caller_sub,
            region=region,
            tenant_kms_key_id=tenant_kms_key_id,
        )
        return _serialise_ws(ws)

    # -- S109 --------------------------------------------------------------- #
    async def list_for_caller(
        self,
        *,
        caller_sub: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List workspaces the caller belongs to (page-bounded)."""
        if page < 1:
            raise WorkspaceError("page must be >= 1")
        if not 1 <= page_size <= 200:
            raise WorkspaceError("page_size must be 1..200")
        items = await self.workspaces.list_for_user(caller_sub)
        items.sort(key=lambda w: w.created_at)
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        return {
            "items": [_serialise_ws(w) for w in page_items],
            "page": page,
            "page_size": page_size,
            "total": len(items),
        }

    # -- S110 --------------------------------------------------------------- #
    async def get(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        request_region: str | None = None,
    ) -> dict[str, Any]:
        """Read a single workspace; caller must be a member."""
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        return _serialise_ws(ws)

    async def forward_data_plane_call(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        method: str,
        path: str,
        transport: DataPlaneTransport,
        body: Mapping[str, Any] | None = None,
        request_region: str | None = None,
    ) -> dict[str, Any]:
        """Forward a workspace-scoped data-plane call to its pinned region."""
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        result = await self.region_router.forward(
            workspace=ws,
            method=method,
            path=path,
            transport=transport,
            json_body=body,
        )
        return {
            "status_code": result.status_code,
            "body": result.body,
            "headers": result.headers,
            "region": result.region,
            "url": result.url,
            "latency_ms": result.latency_ms,
        }

    async def load_data_export(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        export_id: str,
        export_region: str,
        store: DataExportStore,
        request_region: str | None = None,
    ) -> dict[str, Any]:
        """Load export metadata only from the workspace's pinned region."""
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.OWNER,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        try:
            self.workspaces.require_same_region(
                workspace_region=ws.region,
                request_region=export_region,
            )
        except RegionError as exc:
            raise AuthorisationError("cross-region data export denied") from exc
        record = await store.load_workspace_export(
            workspace_id=workspace_id,
            export_id=export_id,
            region=ws.region,
        )
        return dict(record)

    async def patch(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        body: dict[str, Any],
        request_region: str | None = None,
    ) -> dict[str, Any]:
        """Update a workspace. Owner-only."""
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.OWNER,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        name_value = body.get("name")
        if name_value is not None and not isinstance(name_value, str):
            raise WorkspaceError("name must be a string")
        if "region" in body:
            region_value = body["region"]
            if not isinstance(region_value, str):
                raise WorkspaceError("region must be a string")
            raise WorkspaceError("workspace.region is immutable after create")
        if "tenant_kms_key_id" in body:
            raise WorkspaceError("workspace.tenant_kms_key_id is immutable after create")
        new_ws = await self.workspaces.update(
            workspace_id=workspace_id,
            actor_sub=caller_sub,
            name=name_value,
        )
        return _serialise_ws(new_ws)

    # -- S112 --------------------------------------------------------------- #
    async def list_members(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        request_region: str | None = None,
    ) -> dict[str, Any]:
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        members = await self.workspaces.list_members(workspace_id)
        members.sort(key=lambda m: m.user_sub)
        return {"items": [_serialise_member(m) for m in members]}

    async def add_member(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        body: dict[str, Any],
        request_region: str | None = None,
    ) -> dict[str, Any]:
        """Direct membership add (S112). Owner-only.

        Note: S111 (email-based invite) is a separate story; this is
        the synchronous "I already know the user_sub" path used by
        admin tooling and by the invite-acceptance handler in S111.
        """
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.OWNER,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        target_sub = _require_str("user_sub", body.get("user_sub"))
        role = _require_role("role", body.get("role", Role.MEMBER.value))
        if role is Role.OWNER:
            # Adding a second owner is fine; we just guard against
            # accidentally promoting via the add path -- the canonical
            # promote path is :meth:`update_member_role`.
            existing = await self.workspaces.role_of(workspace_id=workspace_id, user_sub=target_sub)
            if existing is not None:
                raise WorkspaceError("user is already a member; use PATCH to change role")
        membership = await self.workspaces.add_member(
            workspace_id=workspace_id, user_sub=target_sub, role=role
        )
        return _serialise_member(membership)

    async def remove_member(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        user_sub: str,
        request_region: str | None = None,
    ) -> dict[str, Any]:
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.OWNER,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        await self.workspaces.remove_member(
            workspace_id=workspace_id,
            user_sub=user_sub,
            actor_sub=caller_sub,
        )
        return {"workspace_id": str(workspace_id), "user_sub": user_sub, "removed": True}

    async def update_member_role(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        user_sub: str,
        body: dict[str, Any],
        request_region: str | None = None,
    ) -> dict[str, Any]:
        ws, _ = await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.OWNER,
        )
        self._require_request_region(workspace=ws, request_region=request_region)
        role = _require_role("role", body.get("role"))
        updated = await self.workspaces.update_role(
            workspace_id=workspace_id,
            user_sub=user_sub,
            role=role,
            actor_sub=caller_sub,
        )
        return _serialise_member(updated)


__all__ = ["AuthorisationError", "WorkspaceAPI"]
