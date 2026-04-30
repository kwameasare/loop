"""dp_0001 initial data plane: conversations, turns, memory, tool_calls

Revision ID: dp_0001_initial
Revises:
Create Date: 2026-04-30 02:20:00

Mirrors loop_implementation/data/SCHEMA.md sections 3.1-3.3. Every table here is
tenanted (workspace_id NOT NULL) and ships with row-level security enforcing
``current_setting('loop.workspace_id')`` -- see ADR-020.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "dp_0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TENANTED_TABLES = (
    "conversations",
    "turns",
    "memory_user",
    "memory_bot",
    "tool_calls",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # conversations -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE conversations (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     UUID NOT NULL,
            agent_id         UUID NOT NULL,
            channel_type     TEXT NOT NULL,
            user_id          TEXT NOT NULL,
            started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            status           TEXT NOT NULL DEFAULT 'active'
                               CHECK (status IN ('active','idle','closed','escalated')),
            operator_user_id UUID,
            metadata_json    JSONB NOT NULL DEFAULT '{}'
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_conv_workspace_last "
        "ON conversations (workspace_id, last_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_conv_agent_user ON conversations (agent_id, user_id)"
    )

    # turns -------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE turns (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            seq             INTEGER NOT NULL,
            role            TEXT NOT NULL CHECK (role IN ('user','agent','tool','system','operator')),
            content_json    JSONB NOT NULL,
            token_in        INTEGER,
            token_out       INTEGER,
            cost_usd        NUMERIC(8,5),
            latency_ms      INTEGER,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at        TIMESTAMPTZ,
            UNIQUE(conversation_id, seq)
        )
        """
    )
    op.execute("CREATE INDEX idx_turns_conv_seq ON turns (conversation_id, seq)")

    # memory tiers ------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE memory_user (
            workspace_id UUID NOT NULL,
            agent_id     UUID NOT NULL,
            user_id      TEXT NOT NULL,
            key          TEXT NOT NULL,
            value_json   JSONB NOT NULL,
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, agent_id, user_id, key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_bot (
            workspace_id UUID NOT NULL,
            agent_id     UUID NOT NULL,
            key          TEXT NOT NULL,
            value_json   JSONB NOT NULL,
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, agent_id, key)
        )
        """
    )

    # tool_calls --------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE tool_calls (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id  UUID NOT NULL,
            turn_id       UUID NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
            mcp_server_id UUID NOT NULL,
            tool_name     TEXT NOT NULL,
            args_json     JSONB NOT NULL,
            result_json   JSONB,
            error         TEXT,
            latency_ms    INTEGER,
            cost_usd      NUMERIC(8,5),
            started_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_tool_calls_turn ON tool_calls (turn_id)")

    # Row-level security on every tenanted table ------------------------------
    # The runtime sets `loop.workspace_id` per-connection via SET LOCAL so
    # accidental cross-tenant queries are physically impossible. ADR-020.
    for table in _TENANTED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
              USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
              WITH CHECK (workspace_id = current_setting('loop.workspace_id', true)::uuid)
            """
        )

    _ = sa  # reserved for future revisions using sa.Table helpers


def downgrade() -> None:
    for table in (
        "tool_calls",
        "memory_bot",
        "memory_user",
        "turns",
        "conversations",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
