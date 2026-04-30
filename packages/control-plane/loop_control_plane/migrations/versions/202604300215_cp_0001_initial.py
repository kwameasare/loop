"""cp_0001 initial control plane: workspaces, users, members, api_keys, agents

Revision ID: cp_0001_initial
Revises:
Create Date: 2026-04-30 02:15:00

Mirrors loop_implementation/data/SCHEMA.md sections 2.1-2.2 (identity, secrets,
agent registration). Audit log + deployment events follow in cp_0002.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cp_0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Required extensions -----------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # workspaces --------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE workspaces (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name              TEXT NOT NULL,
            slug              TEXT NOT NULL UNIQUE,
            plan              TEXT NOT NULL DEFAULT 'hobby'
                                CHECK (plan IN ('hobby','pro','team','enterprise')),
            region            TEXT NOT NULL DEFAULT 'na-east',
            tenant_kms_key_id TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at        TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_workspaces_slug ON workspaces(slug) WHERE deleted_at IS NULL"
    )

    # users -------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE users (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email         CITEXT NOT NULL UNIQUE,
            full_name     TEXT,
            auth_provider TEXT NOT NULL,
            auth_subject  TEXT NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(auth_provider, auth_subject)
        )
        """
    )

    # workspace_members -------------------------------------------------------
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

    # api_keys ----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE api_keys (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name         TEXT NOT NULL,
            prefix       TEXT NOT NULL,
            hash         BYTEA NOT NULL,
            created_by   UUID REFERENCES users(id),
            scopes       TEXT[] NOT NULL DEFAULT '{}',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            revoked_at   TIMESTAMPTZ,
            UNIQUE(workspace_id, prefix)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id) WHERE revoked_at IS NULL"
    )

    # agent_secrets -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE agent_secrets (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            agent_id        UUID,
            name            TEXT NOT NULL,
            secret_ref      TEXT NOT NULL,
            tenant_kms_key  TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            rotated_at      TIMESTAMPTZ,
            UNIQUE(workspace_id, agent_id, name)
        )
        """
    )

    # agents ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE agents (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            slug         TEXT NOT NULL,
            display_name TEXT NOT NULL,
            current_version_id UUID,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at  TIMESTAMPTZ,
            UNIQUE(workspace_id, slug)
        )
        """
    )
    op.execute("CREATE INDEX idx_agents_workspace ON agents(workspace_id)")

    # agent_versions ----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE agent_versions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            version         TEXT NOT NULL,
            artifact_uri    TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            created_by      UUID REFERENCES users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            promoted_to     TEXT NOT NULL DEFAULT 'staging'
                              CHECK (promoted_to IN ('dev','staging','prod','rolled_back')),
            UNIQUE(agent_id, version)
        )
        """
    )
    op.execute(
        "ALTER TABLE agents ADD CONSTRAINT fk_agents_current_version "
        "FOREIGN KEY (current_version_id) REFERENCES agent_versions(id)"
    )

    # Tenant isolation: control plane is admin-tier — all queries already
    # carry workspace_id filters, but enable RLS for defence in depth on
    # the customer-data-bearing tables.
    for table in ("api_keys", "agent_secrets", "agents", "agent_versions"):
        # agent_versions reaches workspace via its agent — RLS uses a subquery.
        if table == "agent_versions":
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"""
                CREATE POLICY tenant_isolation ON {table}
                  USING (
                    agent_id IN (
                      SELECT id FROM agents
                       WHERE workspace_id = current_setting('loop.workspace_id', true)::uuid
                    )
                  )
                """  # noqa: S608  -- {table} is a hardcoded literal, not user input
            )
        else:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"""
                CREATE POLICY tenant_isolation ON {table}
                  USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
                """
            )

    _ = sa  # keep import for downstream revisions that use sa.* helpers


def downgrade() -> None:
    for table in (
        "agent_versions",
        "agents",
        "agent_secrets",
        "api_keys",
        "workspace_members",
        "users",
        "workspaces",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
