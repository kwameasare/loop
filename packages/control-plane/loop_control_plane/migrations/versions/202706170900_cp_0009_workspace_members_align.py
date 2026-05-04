"""cp_0008 align workspace_members + workspaces with the in-memory model [P0.2].

The cp_0001 schema for ``workspace_members`` was sketched against an
older identity design that assumed every actor would be provisioned
into the ``users`` table first; the cp-api today threads an Auth0
``sub`` string through every call-site and never writes a ``users``
row. ``WorkspaceService`` (in-memory) keys memberships on that string
directly. ``PostgresWorkspaceService`` (this PR series) needs the
schema to match that contract or the in-memory and Postgres
implementations would have diverging surface — ``add_member`` would
need a user-creation step in one but not the other.

This migration aligns ``workspace_members`` to the in-memory model:

* Drop ``user_id UUID REFERENCES users(id)`` and ``invited_by UUID``;
  add ``user_sub TEXT NOT NULL``.
* Replace the role CHECK constraint to match the
  :class:`~loop_control_plane.workspaces.Role` enum
  (``owner | admin | member | viewer``) — the previous CHECK admitted
  ``editor`` / ``operator`` which the in-memory enum never produced.

It also adds ``created_by TEXT NOT NULL`` to ``workspaces`` because
the in-memory :class:`Workspace` Pydantic model requires it and
``PostgresWorkspaceService.create()`` must round-trip the same shape.

There is no data-loss risk: the previous ``workspace_members`` /
``workspaces`` tables only existed in dev/test databases (cp-api was
in-memory in production), so the destructive recreate is safe.

Revision ID: cp_0009_workspace_members_align
Revises: cp_0008_refresh_tokens
Create Date: 2027-06-17 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0009_workspace_members_align"
down_revision: str | Sequence[str] | None = "cp_0008_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # workspace_members: drop & recreate with the aligned shape.
    op.execute("DROP TABLE IF EXISTS workspace_members CASCADE")
    op.execute(
        """
        CREATE TABLE workspace_members (
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_sub     TEXT NOT NULL,
            role         TEXT NOT NULL
                          CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, user_sub)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_workspace_members_user_sub ON workspace_members(user_sub)"
    )

    # workspaces: add created_by; drop the default after the column is
    # in place so future INSERTs that forget to supply it raise a
    # NOT NULL violation rather than silently storing ''.
    op.execute(
        "ALTER TABLE workspaces ADD COLUMN created_by TEXT NOT NULL DEFAULT ''"
    )
    op.execute("ALTER TABLE workspaces ALTER COLUMN created_by DROP DEFAULT")


def downgrade() -> None:
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS created_by")
    op.execute("DROP TABLE IF EXISTS workspace_members CASCADE")
    # Restore the cp_0001 shape so a downgrade-then-upgrade chain works.
    op.execute(
        """
        CREATE TABLE workspace_members (
            workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
            role         TEXT NOT NULL CHECK (role IN ('owner','admin','editor','operator','viewer')),
            invited_by   UUID REFERENCES users(id),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, user_id)
        )
        """
    )
