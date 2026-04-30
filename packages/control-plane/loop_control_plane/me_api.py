"""``GET /v1/me`` facade (S106).

Returns the authenticated user's identity plus the workspaces they
belong to. The response shape mirrors ``UserResponse`` in
``loop_implementation/api/openapi.yaml``.

The route handler does:

    me = await MeAPI(workspace_service, user_directory).get_me(user_sub)

and this module produces a serialisation-ready dict so the FastAPI
shim is a one-liner.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.workspaces import Workspace, WorkspaceService

__all__ = [
    "MeAPI",
    "MeResponse",
    "UnknownUser",
    "UserDirectory",
    "UserProfile",
    "WorkspaceSummary",
]


class UnknownUser(LookupError):  # noqa: N818  -- domain-named lookup miss
    """The authenticated subject has no provisioned profile."""


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    sub: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=128)
    created_at: datetime


class WorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    name: str
    slug: str
    role: str


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    profile: UserProfile
    workspaces: tuple[WorkspaceSummary, ...]


# A lookup that returns the bare profile for a verified ``sub``.
UserDirectory = Callable[[str], Awaitable[UserProfile | None]]


@dataclass(frozen=True)
class MeAPI:
    workspace_service: WorkspaceService
    user_directory: UserDirectory

    async def get_me(self, user_sub: str) -> MeResponse:
        profile = await self.user_directory(user_sub)
        if profile is None:
            raise UnknownUser(user_sub)
        workspaces: list[Workspace] = await self.workspace_service.list_for_user(
            user_sub
        )
        # Membership lookup is N+1 against the in-memory store, but
        # trivial against the SQL implementation (single JOIN).
        summaries: list[WorkspaceSummary] = []
        for ws in workspaces:
            role = await self.workspace_service.role_of(
                workspace_id=ws.id, user_sub=user_sub
            )
            if role is None:  # pragma: no cover — list_for_user is the source.
                continue
            summaries.append(
                WorkspaceSummary(
                    id=ws.id, name=ws.name, slug=ws.slug, role=role.value
                )
            )
        # Stable order: alphabetical by slug — frontend picker depends
        # on it for the workspace switcher.
        summaries.sort(key=lambda s: s.slug)
        return MeResponse(profile=profile, workspaces=tuple(summaries))

    async def to_dict(self, user_sub: str) -> dict[str, Any]:
        """Convenience helper for the route handler — returns plain JSON."""
        me = await self.get_me(user_sub)
        return me.model_dump(mode="json")
