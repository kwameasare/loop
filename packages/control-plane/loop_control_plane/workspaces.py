"""Workspace + membership domain services.

Two implementations live here: :class:`WorkspaceService` (in-memory,
the long-standing default for tests + air-gapped dev) and
:class:`PostgresWorkspaceService` (P0.2, Postgres-backed for
production). They share the same async surface and return identical
:class:`Workspace` / :class:`Membership` Pydantic models, so the
cp-api routes don't care which one is wired in.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane.regions import (
    RegionError,
    RegionRegistry,
    default_region_registry,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


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
    region: str = Field(default="na-east", min_length=1)
    tenant_kms_key_id: str = Field(min_length=1, max_length=512)
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

    def __init__(self, regions: RegionRegistry | None = None) -> None:
        self._workspaces: dict[UUID, Workspace] = {}
        self._slugs: dict[str, UUID] = {}
        self._memberships: dict[tuple[UUID, str], Membership] = {}
        self._regions = regions or default_region_registry()
        self._lock = asyncio.Lock()

    def require_same_region(self, *, workspace_region: str, request_region: str) -> None:
        self._regions.require_same(
            workspace_region=workspace_region,
            request_region=request_region,
        )

    async def create(
        self,
        *,
        name: str,
        slug: str,
        owner_sub: str,
        region: str | None = None,
        tenant_kms_key_id: str | None = None,
    ) -> Workspace:
        async with self._lock:
            if slug in self._slugs:
                raise WorkspaceError(f"slug already taken: {slug}")
            region_slug = region or self._regions.default_region
            try:
                self._regions.require(region_slug)
            except RegionError as exc:
                raise WorkspaceError(str(exc)) from exc
            ws = Workspace(
                id=uuid4(),
                name=name,
                slug=slug,
                region=region_slug,
                tenant_kms_key_id=tenant_kms_key_id or f"vault://transit/workspace/{slug}",
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

    async def list_members(self, workspace_id: UUID) -> list[Membership]:
        async with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            return [m for (ws, _), m in self._memberships.items() if ws == workspace_id]

    async def remove_member(self, *, workspace_id: UUID, user_sub: str, actor_sub: str) -> None:
        """Remove a membership.

        Refuses to remove the last owner of a workspace -- the workspace
        must always have at least one owner. The actor must already be
        a member; role-level enforcement (only owners may remove others)
        is the API layer's responsibility via :func:`authorize_workspace_access`.
        """
        async with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            if (workspace_id, actor_sub) not in self._memberships:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            target = self._memberships.get((workspace_id, user_sub))
            if target is None:
                raise WorkspaceError(f"{user_sub} is not a member")
            if target.role is Role.OWNER:
                owners = [
                    m
                    for (ws, _), m in self._memberships.items()
                    if ws == workspace_id and m.role is Role.OWNER
                ]
                if len(owners) == 1:
                    raise WorkspaceError("cannot remove the last owner")
            self._memberships.pop((workspace_id, user_sub))

    async def update_role(
        self,
        *,
        workspace_id: UUID,
        user_sub: str,
        role: Role,
        actor_sub: str,
    ) -> Membership:
        """Change the role of an existing member.

        Refuses to demote the last owner. Returns the updated membership.
        """
        async with self._lock:
            if workspace_id not in self._workspaces:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            if (workspace_id, actor_sub) not in self._memberships:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            target = self._memberships.get((workspace_id, user_sub))
            if target is None:
                raise WorkspaceError(f"{user_sub} is not a member")
            if target.role is Role.OWNER and role is not Role.OWNER:
                owners = [
                    m
                    for (ws, _), m in self._memberships.items()
                    if ws == workspace_id and m.role is Role.OWNER
                ]
                if len(owners) == 1:
                    raise WorkspaceError("cannot demote the last owner")
            updated = Membership(workspace_id=workspace_id, user_sub=user_sub, role=role)
            self._memberships[(workspace_id, user_sub)] = updated
            return updated

    async def update(
        self,
        *,
        workspace_id: UUID,
        actor_sub: str,
        name: str | None = None,
        region: str | None = None,
    ) -> Workspace:
        """Mutate workspace fields. Actor must be a member.

        Owner-only enforcement happens in the API layer via
        :func:`authorize_workspace_access`.
        """
        async with self._lock:
            ws = self._workspaces.get(workspace_id)
            if ws is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            if (workspace_id, actor_sub) not in self._memberships:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            if region is not None:
                raise WorkspaceError("workspace.region is immutable after create")
            updates: dict[str, str] = {}
            if name is not None:
                if not name or len(name) > 64:
                    raise WorkspaceError("name must be 1..64 chars")
                updates["name"] = name
            if not updates:
                return ws
            new_ws = ws.model_copy(update=updates)
            self._workspaces[workspace_id] = new_ws
            return new_ws

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


__all__ = [
    "Membership",
    "PostgresWorkspaceService",
    "Role",
    "Workspace",
    "WorkspaceError",
    "WorkspaceService",
]


# ---------------------------------------------------------------------------
# Postgres-backed service [P0.2]
# ---------------------------------------------------------------------------


class PostgresWorkspaceService:
    """Postgres-backed workspace + membership store.

    Drop-in replacement for :class:`WorkspaceService`: same async
    methods, same :class:`Workspace` / :class:`Membership` return
    types, same :class:`WorkspaceError` failure mode.

    Uses SQLAlchemy 2.0 async (``AsyncEngine`` via
    ``create_async_engine`` on a ``postgresql+psycopg://`` URL). Each
    method opens a short transaction; multi-statement methods that
    enforce invariants (last-owner-cannot-be-removed,
    slug-uniqueness) use ``SELECT ... FOR UPDATE`` to serialise
    concurrent writers.

    Schema lives in ``cp_0001_initial`` (workspaces) +
    ``cp_0008_workspace_members_align`` (workspace_members keyed on
    user_sub TEXT and the in-memory :class:`Role` enum).
    """

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        regions: RegionRegistry | None = None,
    ) -> None:
        self._engine = engine
        self._regions = regions or default_region_registry()

    @classmethod
    def from_url(
        cls,
        database_url: str,
        *,
        echo: bool = False,
        regions: RegionRegistry | None = None,
    ) -> PostgresWorkspaceService:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine, regions=regions)

    # ------------------------------------------------------------- region

    def require_same_region(
        self, *, workspace_region: str, request_region: str
    ) -> None:
        # Sync helper — no DB I/O. Mirrors WorkspaceService exactly.
        self._regions.require_same(
            workspace_region=workspace_region,
            request_region=request_region,
        )

    # ------------------------------------------------------------- create

    async def create(
        self,
        *,
        name: str,
        slug: str,
        owner_sub: str,
        region: str | None = None,
        tenant_kms_key_id: str | None = None,
    ) -> Workspace:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        region_slug = region or self._regions.default_region
        try:
            self._regions.require(region_slug)
        except RegionError as exc:
            raise WorkspaceError(str(exc)) from exc

        kms_key = tenant_kms_key_id or f"vault://transit/workspace/{slug}"
        new_id = uuid4()
        now = datetime.now(UTC)

        try:
            async with self._engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO workspaces (
                            id, name, slug, region, tenant_kms_key_id,
                            created_at, created_by
                        ) VALUES (
                            :id, :name, :slug, :region, :tenant_kms_key_id,
                            :created_at, :created_by
                        )
                        """
                    ),
                    {
                        "id": new_id,
                        "name": name,
                        "slug": slug,
                        "region": region_slug,
                        "tenant_kms_key_id": kms_key,
                        "created_at": now,
                        "created_by": owner_sub,
                    },
                )
                await conn.execute(
                    text(
                        """
                        INSERT INTO workspace_members (
                            workspace_id, user_sub, role
                        ) VALUES (:workspace_id, :user_sub, :role)
                        """
                    ),
                    {
                        "workspace_id": new_id,
                        "user_sub": owner_sub,
                        "role": Role.OWNER.value,
                    },
                )
        except IntegrityError as exc:
            # workspaces.slug has a UNIQUE constraint; a duplicate
            # raises IntegrityError. Translate to WorkspaceError so
            # callers see the same surface as the in-memory store.
            raise WorkspaceError(f"slug already taken: {slug}") from exc

        return Workspace(
            id=new_id,
            name=name,
            slug=slug,
            region=region_slug,
            tenant_kms_key_id=kms_key,
            created_at=now,
            created_by=owner_sub,
        )

    # ---------------------------------------------------------------- get

    async def get(self, workspace_id: UUID) -> Workspace:
        from sqlalchemy import text

        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, name, slug, region, tenant_kms_key_id,
                               created_at, created_by
                          FROM workspaces
                         WHERE id = :id AND deleted_at IS NULL
                        """
                    ),
                    {"id": workspace_id},
                )
            ).first()
        if row is None:
            raise WorkspaceError(f"unknown workspace: {workspace_id}")
        return _row_to_workspace(row)

    async def list_for_user(self, user_sub: str) -> list[Workspace]:
        from sqlalchemy import text

        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT w.id, w.name, w.slug, w.region,
                               w.tenant_kms_key_id, w.created_at,
                               w.created_by
                          FROM workspaces AS w
                          JOIN workspace_members AS m
                            ON m.workspace_id = w.id
                         WHERE m.user_sub = :user_sub
                           AND w.deleted_at IS NULL
                         ORDER BY w.created_at ASC
                        """
                    ),
                    {"user_sub": user_sub},
                )
            ).all()
        return [_row_to_workspace(r) for r in rows]

    # -------------------------------------------------------------- members

    async def add_member(
        self, *, workspace_id: UUID, user_sub: str, role: Role
    ) -> Membership:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        try:
            async with self._engine.begin() as conn:
                ws_row = await self._lock_workspace(conn, workspace_id)
                if ws_row is None:
                    raise WorkspaceError(f"unknown workspace: {workspace_id}")
                # ON CONFLICT DO UPDATE matches the in-memory
                # ``self._memberships[(ws, sub)] = m`` overwrite.
                await conn.execute(
                    text(
                        """
                        INSERT INTO workspace_members (workspace_id, user_sub, role)
                        VALUES (:workspace_id, :user_sub, :role)
                        ON CONFLICT (workspace_id, user_sub) DO UPDATE
                           SET role = EXCLUDED.role
                        """
                    ),
                    {
                        "workspace_id": workspace_id,
                        "user_sub": user_sub,
                        "role": role.value,
                    },
                )
        except IntegrityError as exc:
            # The role CHECK constraint is the only IntegrityError
            # path here; the Role enum's ``StrEnum`` values match the
            # CHECK exactly so this branch should be unreachable.
            raise WorkspaceError(str(exc)) from exc
        return Membership(workspace_id=workspace_id, user_sub=user_sub, role=role)

    async def role_of(
        self, *, workspace_id: UUID, user_sub: str
    ) -> Role | None:
        from sqlalchemy import text

        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT role
                          FROM workspace_members
                         WHERE workspace_id = :workspace_id
                           AND user_sub = :user_sub
                        """
                    ),
                    {"workspace_id": workspace_id, "user_sub": user_sub},
                )
            ).first()
        if row is None:
            return None
        return Role(row.role)

    async def list_members(self, workspace_id: UUID) -> list[Membership]:
        from sqlalchemy import text

        async with self._engine.connect() as conn:
            ws_exists = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM workspaces WHERE id = :id AND deleted_at IS NULL"
                    ),
                    {"id": workspace_id},
                )
            ).first()
            if ws_exists is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT user_sub, role
                          FROM workspace_members
                         WHERE workspace_id = :workspace_id
                         ORDER BY created_at ASC
                        """
                    ),
                    {"workspace_id": workspace_id},
                )
            ).all()
        return [
            Membership(
                workspace_id=workspace_id,
                user_sub=r.user_sub,
                role=Role(r.role),
            )
            for r in rows
        ]

    async def remove_member(
        self, *, workspace_id: UUID, user_sub: str, actor_sub: str
    ) -> None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            ws_row = await self._lock_workspace(conn, workspace_id)
            if ws_row is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            # Both the actor and target memberships must be locked
            # so a concurrent owner-removal can't sneak through and
            # leave us ownerless.
            actor = await self._lock_membership(conn, workspace_id, actor_sub)
            if actor is None:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            target = await self._lock_membership(conn, workspace_id, user_sub)
            if target is None:
                raise WorkspaceError(f"{user_sub} is not a member")
            if Role(target.role) is Role.OWNER:
                owner_count = await self._count_owners(conn, workspace_id)
                if owner_count == 1:
                    raise WorkspaceError("cannot remove the last owner")
            await conn.execute(
                text(
                    """
                    DELETE FROM workspace_members
                     WHERE workspace_id = :workspace_id
                       AND user_sub = :user_sub
                    """
                ),
                {"workspace_id": workspace_id, "user_sub": user_sub},
            )

    async def update_role(
        self,
        *,
        workspace_id: UUID,
        user_sub: str,
        role: Role,
        actor_sub: str,
    ) -> Membership:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            ws_row = await self._lock_workspace(conn, workspace_id)
            if ws_row is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            actor = await self._lock_membership(conn, workspace_id, actor_sub)
            if actor is None:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            target = await self._lock_membership(conn, workspace_id, user_sub)
            if target is None:
                raise WorkspaceError(f"{user_sub} is not a member")
            if Role(target.role) is Role.OWNER and role is not Role.OWNER:
                owner_count = await self._count_owners(conn, workspace_id)
                if owner_count == 1:
                    raise WorkspaceError("cannot demote the last owner")
            await conn.execute(
                text(
                    """
                    UPDATE workspace_members
                       SET role = :role
                     WHERE workspace_id = :workspace_id
                       AND user_sub = :user_sub
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "user_sub": user_sub,
                    "role": role.value,
                },
            )
        return Membership(workspace_id=workspace_id, user_sub=user_sub, role=role)

    # --------------------------------------------------------- update / delete

    async def update(
        self,
        *,
        workspace_id: UUID,
        actor_sub: str,
        name: str | None = None,
        region: str | None = None,
    ) -> Workspace:
        from sqlalchemy import text

        if region is not None:
            raise WorkspaceError("workspace.region is immutable after create")
        if name is not None and (not name or len(name) > 64):
            raise WorkspaceError("name must be 1..64 chars")

        async with self._engine.begin() as conn:
            ws_row = await self._lock_workspace(conn, workspace_id)
            if ws_row is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            actor = await self._lock_membership(conn, workspace_id, actor_sub)
            if actor is None:
                raise WorkspaceError(f"actor {actor_sub} is not a member")
            if name is None:
                # No-op update — return the current snapshot, same as
                # WorkspaceService when called with no changes.
                return _row_to_workspace(ws_row)
            await conn.execute(
                text("UPDATE workspaces SET name = :name WHERE id = :id"),
                {"name": name, "id": workspace_id},
            )
            refreshed = await self._lock_workspace(conn, workspace_id)
        # _lock_workspace returns None if the row vanished mid-tx; the
        # FK + serialisation guarantees that won't happen here, but
        # narrow the type for the caller.
        assert refreshed is not None
        return _row_to_workspace(refreshed)

    async def delete(self, *, workspace_id: UUID, actor_sub: str) -> None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            ws_row = await self._lock_workspace(conn, workspace_id)
            if ws_row is None:
                raise WorkspaceError(f"unknown workspace: {workspace_id}")
            actor = await self._lock_membership(conn, workspace_id, actor_sub)
            if actor is None or Role(actor.role) is not Role.OWNER:
                raise WorkspaceError("only the owner may delete a workspace")
            # Hard delete — workspace_members has ON DELETE CASCADE so
            # member rows go with it. Matches the in-memory contract;
            # ``deleted_at`` is left for a future soft-delete migration
            # if/when retention rules require it.
            await conn.execute(
                text("DELETE FROM workspaces WHERE id = :id"),
                {"id": workspace_id},
            )

    # ------------------------------------------------------------- helpers

    async def _lock_workspace(self, conn: object, workspace_id: UUID):  # type: ignore[no-untyped-def]
        """SELECT ... FOR UPDATE on the workspace row.

        Returns the row (with all columns) or ``None`` if the
        workspace doesn't exist or is soft-deleted. The lock is
        released when the surrounding transaction commits.
        """
        from sqlalchemy import text

        return (
            await conn.execute(  # type: ignore[union-attr]
                text(
                    """
                    SELECT id, name, slug, region, tenant_kms_key_id,
                           created_at, created_by
                      FROM workspaces
                     WHERE id = :id AND deleted_at IS NULL
                       FOR UPDATE
                    """
                ),
                {"id": workspace_id},
            )
        ).first()

    async def _lock_membership(self, conn: object, workspace_id: UUID, user_sub: str):  # type: ignore[no-untyped-def]
        from sqlalchemy import text

        return (
            await conn.execute(  # type: ignore[union-attr]
                text(
                    """
                    SELECT user_sub, role
                      FROM workspace_members
                     WHERE workspace_id = :workspace_id
                       AND user_sub = :user_sub
                       FOR UPDATE
                    """
                ),
                {"workspace_id": workspace_id, "user_sub": user_sub},
            )
        ).first()

    async def _count_owners(self, conn: object, workspace_id: UUID) -> int:  # type: ignore[no-untyped-def]
        from sqlalchemy import text

        count = (
            await conn.execute(  # type: ignore[union-attr]
                text(
                    """
                    SELECT count(*) AS n
                      FROM workspace_members
                     WHERE workspace_id = :workspace_id
                       AND role = :role
                    """
                ),
                {"workspace_id": workspace_id, "role": Role.OWNER.value},
            )
        ).scalar_one()
        return int(count)


def _row_to_workspace(row: object) -> Workspace:
    """Build a :class:`Workspace` from a SQLAlchemy Row."""
    return Workspace(
        id=row.id,  # type: ignore[attr-defined]
        name=row.name,  # type: ignore[attr-defined]
        slug=row.slug,  # type: ignore[attr-defined]
        region=row.region,  # type: ignore[attr-defined]
        tenant_kms_key_id=row.tenant_kms_key_id,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        created_by=row.created_by,  # type: ignore[attr-defined]
    )
