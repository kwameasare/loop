"""Workspace-scoped authorisation helper (S107).

Every ``/v1/workspaces/{workspace_id}/*`` route in cp-api needs to
answer two questions before the handler runs:

1. Does the workspace exist? (404 otherwise.)
2. Is the calling identity a member, and does their role meet the
   route's minimum requirement? (403 otherwise.)

This module gives every router the same answer via one async helper,
:func:`authorize_workspace_access`. Routes that only require membership
pass ``required_role=None`` (the default); routes that mutate state
pass ``required_role=Role.ADMIN`` or ``Role.OWNER`` as appropriate.

The role lattice is::

    OWNER > ADMIN > MEMBER > VIEWER

A higher role implicitly satisfies a lower-role requirement.

Why this lives in the package and not in a "FastAPI dependency": the
authorisation rule is a domain rule, not a transport concern. The
HTTP layer is a thin adaptor that turns :class:`AuthorisationError`
into a 403 (or :class:`WorkspaceError` into a 404). Tests exercise
this helper without standing up a web framework.
"""

from __future__ import annotations

from uuid import UUID

from loop_control_plane.workspaces import (
    Membership,
    Role,
    Workspace,
    WorkspaceError,
    WorkspaceService,
)

# Role precedence -- higher index = more powerful. A required role of
# ``Role.MEMBER`` is satisfied by ``Role.ADMIN`` or ``Role.OWNER``.
_ROLE_LADDER: tuple[Role, ...] = (Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER)
_ROLE_RANK: dict[Role, int] = {role: rank for rank, role in enumerate(_ROLE_LADDER)}


class AuthorisationError(PermissionError):
    """Raised when the caller is not allowed to access the workspace.

    Distinct from :class:`WorkspaceError` so the HTTP layer can map
    membership-missing -> 403 (this class) and workspace-missing ->
    404 (``WorkspaceError`` from the service).
    """


def role_satisfies(actual: Role, required: Role) -> bool:
    """Return True iff ``actual`` is at least as powerful as ``required``."""
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]


async def authorize_workspace_access(
    *,
    workspaces: WorkspaceService,
    workspace_id: UUID,
    user_sub: str,
    required_role: Role | None = None,
) -> tuple[Workspace, Membership]:
    """Validate access and return ``(workspace, membership)`` on success.

    Failure modes:

    * Workspace does not exist -> :class:`WorkspaceError` (HTTP 404).
    * Caller is not a member -> :class:`AuthorisationError` (HTTP 403).
    * Caller's role is below ``required_role`` -> :class:`AuthorisationError` (HTTP 403).
    """
    workspace = await workspaces.get(workspace_id)
    role = await workspaces.role_of(workspace_id=workspace_id, user_sub=user_sub)
    if role is None:
        raise AuthorisationError(
            f"{user_sub} is not a member of workspace {workspace_id}"
        )
    if required_role is not None and not role_satisfies(role, required_role):
        raise AuthorisationError(
            f"role '{role.value}' insufficient; '{required_role.value}' required"
        )
    if not isinstance(workspace, Workspace):  # pragma: no cover -- service contract
        raise WorkspaceError("workspace lookup returned non-Workspace value")
    membership = Membership(workspace_id=workspace_id, user_sub=user_sub, role=role)
    return workspace, membership


__all__ = [
    "AuthorisationError",
    "authorize_workspace_access",
    "role_satisfies",
]
