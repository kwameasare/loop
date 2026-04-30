"""Workspace + membership domain services (in-memory backing for now)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Workspace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    created_at: datetime
    created_by: str = Field(min_length=1)


class Membership(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    user_sub: str = Field(min_length=1)
    role: Role


class WorkspaceError(ValueError):
    """Raised on duplicate slug, missing workspace, or auth violations."""


class WorkspaceService:
    """Async, in-memory workspace store. Real impl swaps in postgres."""

    def __init__(self) -> None:
        self._workspaces: dict[UUID, Workspace] = {}
        self._slugs: dict[str, UUID] = {}
        self._memberships: dict[tuple[UUID, str], Membership] = {}
        self._lock = asyncio.Lock()

    async def create(self, *, name: str, slug: str, owner_sub: str) -> Workspace:
        async with self._lock:
            if slug in self._slugs:
                raise WorkspaceError(f"slug already taken: {slug}")
            ws = Workspace(
                id=uuid4(),
                name=name,
                slug=slug,
                created_at=datetime.now(UTC),
                created_by=owner_sub,
            )
            self._workspaces[ws.id] = ws
            self._slugs[slug] = ws.id
            self._memberships[(ws.id, owner_sub)] = Membership(
                workspace_id=ws.id, user_sub=owner_sub, role=Role.OWNER
            )
            return ws

    async def get(self, workspace_id: UUID) -> Workspace:
        async with self._lock:
            ws = self._workspaces.get(workspace_id)
            if ws is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            return ws

    async def list_for_user(self, user_sub: str) -> list[Workspace]:
        async with self._lock:
            ids = [ws_id for (ws_id, sub) in self._memberships if sub == user_sub]
            return [self._workspaces[i] for i in ids]

    async def add_member(self, *, workspace_id: UUID, user_sub: str, role: Role) -> Membership:
        async with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            m = Membership(workspace_id=workspace_id, user_sub=user_sub, role=role)
            self._memberships[(workspace_id, user_sub)] = m
            return m

    async def role_of(self, *, workspace_id: UUID, user_sub: str) -> Role | None:
        async with self._lock:
            m = self._memberships.get((workspace_id, user_sub))
            return m.role if m else None

    async def delete(self, *, workspace_id: UUID, actor_sub: str) -> None:
        async with self._lock:
            ws = self._workspaces.get(workspace_id)
            if ws is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            m = self._memberships.get((workspace_id, actor_sub))
            if m is None or m.role is not Role.OWNER:
                raise WorkspaceError("only the owner may delete a workspace")
            self._workspaces.pop(workspace_id)
            self._slugs.pop(ws.slug, None)
            for key in [k for k in self._memberships if k[0] == workspace_id]:
                self._memberships.pop(key, None)


__all__ = ["Membership", "Role", "Workspace", "WorkspaceError", "WorkspaceService"]
