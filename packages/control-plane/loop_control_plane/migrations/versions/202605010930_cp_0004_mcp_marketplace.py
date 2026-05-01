"""cp_0004 MCP marketplace registry, installs, reviews, and telemetry.

Revision ID: cp_0004_mcp_marketplace
Revises: cp_0003_operator_assignments
Create Date: 2026-05-01 09:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0004_mcp_marketplace"
down_revision: str | Sequence[str] | None = "cp_0003_operator_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE mcp_servers (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug            TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            publisher       TEXT NOT NULL,
            description     TEXT NOT NULL,
            categories      TEXT[] NOT NULL DEFAULT '{}',
            verified        BOOLEAN NOT NULL DEFAULT false,
            signed_by       TEXT NOT NULL,
            manifest_uri    TEXT NOT NULL,
            latest_version  TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE mcp_server_versions (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            server_id               UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
            version                 TEXT NOT NULL,
            manifest_digest         TEXT NOT NULL,
            image_digest            TEXT NOT NULL,
            manifest_uri            TEXT NOT NULL,
            signature               TEXT NOT NULL,
            signed_by               TEXT NOT NULL,
            tools                   JSONB NOT NULL DEFAULT '[]',
            scopes                  TEXT[] NOT NULL DEFAULT '{}',
            verified                BOOLEAN NOT NULL DEFAULT false,
            active                  BOOLEAN NOT NULL DEFAULT true,
            integration_test_green  BOOLEAN NOT NULL DEFAULT false,
            quality_score           INTEGER NOT NULL DEFAULT 0
                                    CHECK (quality_score >= 0 AND quality_score <= 100),
            published_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (server_id, version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE mcp_agent_installs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL,
            agent_id            UUID NOT NULL,
            server_id           UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
            version             TEXT NOT NULL,
            installed_by_sub    TEXT NOT NULL,
            installed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, agent_id, server_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE mcp_server_reviews (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id         UUID NOT NULL,
            server_id            UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
            rating               INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            body                 TEXT NOT NULL,
            moderation_required  BOOLEAN NOT NULL DEFAULT false,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, server_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE mcp_server_usage (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       UUID,
            server_id          UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
            install_count      INTEGER NOT NULL DEFAULT 0 CHECK (install_count >= 0),
            call_count         INTEGER NOT NULL DEFAULT 0 CHECK (call_count >= 0),
            last_called_at     TIMESTAMPTZ,
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, server_id)
        )
        """
    )
    op.execute("CREATE INDEX mcp_servers_category_idx ON mcp_servers USING GIN (categories)")
    op.execute("CREATE INDEX mcp_servers_quality_idx ON mcp_servers (latest_version, verified)")
    op.execute(
        "CREATE INDEX mcp_server_versions_quality_idx "
        "ON mcp_server_versions (quality_score DESC, published_at DESC)"
    )
    for table in ("mcp_agent_installs", "mcp_server_reviews", "mcp_server_usage"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation
                ON {table}
                USING (
                    workspace_id IS NULL
                    OR workspace_id = current_setting('loop.workspace_id', true)::uuid
                )
                WITH CHECK (
                    workspace_id IS NULL
                    OR workspace_id = current_setting('loop.workspace_id', true)::uuid
                )
            """
        )


def downgrade() -> None:
    for table in ("mcp_server_usage", "mcp_server_reviews", "mcp_agent_installs"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS mcp_server_versions_quality_idx")
    op.execute("DROP INDEX IF EXISTS mcp_servers_quality_idx")
    op.execute("DROP INDEX IF EXISTS mcp_servers_category_idx")
    op.execute("DROP TABLE mcp_server_usage")
    op.execute("DROP TABLE mcp_server_reviews")
    op.execute("DROP TABLE mcp_agent_installs")
    op.execute("DROP TABLE mcp_server_versions")
    op.execute("DROP TABLE mcp_servers")
