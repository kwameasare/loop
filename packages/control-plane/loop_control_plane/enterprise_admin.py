"""Enterprise signup + workspace-invite persistence.

Two stores back the enterprise-admin / system-admin surfaces:

* :class:`EnterpriseSignupStore` — captures pending tenant-onboarding
  intents from the public ``/v1/enterprise/signups`` form. Stays
  ``pending_review`` until a system-admin approves it.
* :class:`WorkspaceInviteStore` — captures pending admin/member
  invites per workspace, including the synthetic owner-invite minted
  when an enterprise signup gets approved.

Both have an in-memory implementation for dev/tests and a Postgres-
backed implementation (cp_0014) for production. The async surface is
identical so the route handlers don't care which one is wired in.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "EnterpriseSignup",
    "EnterpriseSignupStore",
    "InMemoryEnterpriseSignupStore",
    "InMemoryWorkspaceInviteStore",
    "PostgresEnterpriseSignupStore",
    "PostgresWorkspaceInviteStore",
    "WorkspaceInvite",
    "WorkspaceInviteStore",
]


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


class EnterpriseSignup(BaseModel):
    """A captured enterprise-onboarding intent.

    ``status`` transitions: ``pending_review`` → ``approved`` (via a
    system-admin) or ``rejected`` (not wired yet — placeholder for the
    eventual reject route).
    """

    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=64)
    organization_name: str
    workspace_slug: str
    admin_name: str
    admin_email: str
    company_size: str
    region: str
    primary_use_case: str
    channel_priorities: tuple[str, ...] = ()
    compliance_needs: tuple[str, ...] = ()
    sso_required: bool = False
    status: str = "pending_review"
    created_at: datetime
    updated_at: datetime
    approved_workspace_id: str | None = None
    approved_by: str | None = None
    admin_invite_id: str | None = None


class WorkspaceInvite(BaseModel):
    """A pending member/admin invite on a workspace."""

    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=64)
    workspace_id: UUID
    email: str
    role: str
    full_name: str | None = None
    note: str | None = None
    status: str = "pending"
    created_at: datetime
    expires_at: datetime
    created_by: str
    invite_url: str


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------


class EnterpriseSignupStore:
    """In-memory store. Holds an asyncio.Lock around the dict so two
    concurrent approvals can't corrupt one signup's state."""

    def __init__(self) -> None:
        self._records: dict[str, EnterpriseSignup] = {}
        self._lock = asyncio.Lock()

    async def create(self, signup: EnterpriseSignup) -> None:
        async with self._lock:
            self._records[signup.id] = signup

    async def get(self, signup_id: str) -> EnterpriseSignup | None:
        async with self._lock:
            return self._records.get(signup_id)

    async def list_all(self) -> list[EnterpriseSignup]:
        async with self._lock:
            return list(self._records.values())

    async def update_approval(
        self,
        *,
        signup_id: str,
        status: str,
        approved_workspace_id: str | None,
        approved_by: str | None,
        admin_invite_id: str | None,
        updated_at: datetime,
    ) -> EnterpriseSignup:
        async with self._lock:
            record = self._records.get(signup_id)
            if record is None:
                raise KeyError(signup_id)
            updated = record.model_copy(
                update={
                    "status": status,
                    "approved_workspace_id": approved_workspace_id,
                    "approved_by": approved_by,
                    "admin_invite_id": admin_invite_id,
                    "updated_at": updated_at,
                }
            )
            self._records[signup_id] = updated
            return updated


# Alias kept for type hints — the in-memory store is the canonical
# Protocol-shaped class (no separate Protocol; we duck-type).
InMemoryEnterpriseSignupStore = EnterpriseSignupStore


class WorkspaceInviteStore:
    """In-memory store, keyed by invite id; secondary index by workspace."""

    def __init__(self) -> None:
        self._records: dict[str, WorkspaceInvite] = {}
        self._by_workspace: dict[UUID, list[str]] = {}
        self._lock = asyncio.Lock()

    async def create(self, invite: WorkspaceInvite) -> None:
        async with self._lock:
            self._records[invite.id] = invite
            self._by_workspace.setdefault(invite.workspace_id, []).append(invite.id)

    async def get(self, invite_id: str) -> WorkspaceInvite | None:
        async with self._lock:
            return self._records.get(invite_id)

    async def list_for_workspace(
        self, workspace_id: UUID
    ) -> list[WorkspaceInvite]:
        async with self._lock:
            ids = list(self._by_workspace.get(workspace_id, ()))
            return [self._records[i] for i in ids if i in self._records]

    async def list_all(self) -> list[WorkspaceInvite]:
        async with self._lock:
            return list(self._records.values())


InMemoryWorkspaceInviteStore = WorkspaceInviteStore


# ---------------------------------------------------------------------------
# Postgres stores
# ---------------------------------------------------------------------------


class PostgresEnterpriseSignupStore:
    """Postgres-backed signup store — drop-in for
    :class:`EnterpriseSignupStore`.

    Schema lives in ``cp_0014_enterprise_admin_tables``. The async
    engine is shared with the other Postgres-backed cp services via
    ``LOOP_CP_DB_URL``.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    @classmethod
    def from_url(
        cls, database_url: str, *, echo: bool = False
    ) -> PostgresEnterpriseSignupStore:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine)

    async def create(self, signup: EnterpriseSignup) -> None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO enterprise_signups (
                        id, organization_name, workspace_slug,
                        admin_name, admin_email, company_size, region,
                        primary_use_case, channel_priorities,
                        compliance_needs, sso_required, status,
                        created_at, updated_at, approved_workspace_id,
                        approved_by, admin_invite_id
                    ) VALUES (
                        :id, :organization_name, :workspace_slug,
                        :admin_name, :admin_email, :company_size, :region,
                        :primary_use_case, :channel_priorities,
                        :compliance_needs, :sso_required, :status,
                        :created_at, :updated_at, :approved_workspace_id,
                        :approved_by, :admin_invite_id
                    )
                    """
                ),
                {
                    **signup.model_dump(),
                    "channel_priorities": list(signup.channel_priorities),
                    "compliance_needs": list(signup.compliance_needs),
                },
            )

    async def get(self, signup_id: str) -> EnterpriseSignup | None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT * FROM enterprise_signups WHERE id = :id"
                ),
                {"id": signup_id},
            )
            row = result.mappings().first()
        return _row_to_signup(row) if row else None

    async def list_all(self) -> list[EnterpriseSignup]:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM enterprise_signups ORDER BY created_at")
            )
            rows = result.mappings().all()
        return [_row_to_signup(row) for row in rows]

    async def update_approval(
        self,
        *,
        signup_id: str,
        status: str,
        approved_workspace_id: str | None,
        approved_by: str | None,
        admin_invite_id: str | None,
        updated_at: datetime,
    ) -> EnterpriseSignup:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    UPDATE enterprise_signups
                       SET status = :status,
                           approved_workspace_id = :approved_workspace_id,
                           approved_by = :approved_by,
                           admin_invite_id = :admin_invite_id,
                           updated_at = :updated_at
                     WHERE id = :id
                     RETURNING *
                    """
                ),
                {
                    "id": signup_id,
                    "status": status,
                    "approved_workspace_id": approved_workspace_id,
                    "approved_by": approved_by,
                    "admin_invite_id": admin_invite_id,
                    "updated_at": updated_at,
                },
            )
            row = result.mappings().first()
        if row is None:
            raise KeyError(signup_id)
        return _row_to_signup(row)


class PostgresWorkspaceInviteStore:
    """Postgres-backed invite store — drop-in for
    :class:`WorkspaceInviteStore`. Schema in cp_0014."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    @classmethod
    def from_url(
        cls, database_url: str, *, echo: bool = False
    ) -> PostgresWorkspaceInviteStore:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine)

    async def create(self, invite: WorkspaceInvite) -> None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO workspace_invites (
                        id, workspace_id, email, role, full_name,
                        note, status, created_at, expires_at,
                        created_by, invite_url
                    ) VALUES (
                        :id, :workspace_id, :email, :role, :full_name,
                        :note, :status, :created_at, :expires_at,
                        :created_by, :invite_url
                    )
                    """
                ),
                invite.model_dump(),
            )

    async def get(self, invite_id: str) -> WorkspaceInvite | None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM workspace_invites WHERE id = :id"),
                {"id": invite_id},
            )
            row = result.mappings().first()
        return _row_to_invite(row) if row else None

    async def list_for_workspace(
        self, workspace_id: UUID
    ) -> list[WorkspaceInvite]:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT * FROM workspace_invites
                     WHERE workspace_id = :workspace_id
                     ORDER BY created_at
                    """
                ),
                {"workspace_id": workspace_id},
            )
            rows = result.mappings().all()
        return [_row_to_invite(row) for row in rows]

    async def list_all(self) -> list[WorkspaceInvite]:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM workspace_invites ORDER BY created_at")
            )
            rows = result.mappings().all()
        return [_row_to_invite(row) for row in rows]


def _row_to_signup(row: Any) -> EnterpriseSignup:
    return EnterpriseSignup(
        id=row["id"],
        organization_name=row["organization_name"],
        workspace_slug=row["workspace_slug"],
        admin_name=row["admin_name"],
        admin_email=row["admin_email"],
        company_size=row["company_size"],
        region=row["region"],
        primary_use_case=row["primary_use_case"],
        channel_priorities=tuple(row["channel_priorities"] or ()),
        compliance_needs=tuple(row["compliance_needs"] or ()),
        sso_required=bool(row["sso_required"]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        approved_workspace_id=row["approved_workspace_id"],
        approved_by=row["approved_by"],
        admin_invite_id=row["admin_invite_id"],
    )


def _row_to_invite(row: Any) -> WorkspaceInvite:
    return WorkspaceInvite(
        id=row["id"],
        workspace_id=row["workspace_id"],
        email=row["email"],
        role=row["role"],
        full_name=row["full_name"],
        note=row["note"],
        status=row["status"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        created_by=row["created_by"],
        invite_url=row["invite_url"],
    )
