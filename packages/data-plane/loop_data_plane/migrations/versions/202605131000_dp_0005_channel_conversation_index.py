"""dp_0005_channel_conversation_index: persistent channel conversation index

Revision ID: dp_0005_channel_conversation_index
Revises: dp_0004_kb_lexical_index
Create Date: 2026-05-13 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0005_channel_conversation_index"
down_revision: str | Sequence[str] | None = "dp_0004_kb_lexical_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE channel_conversation_index (
            workspace_id      UUID NOT NULL,
            channel           TEXT NOT NULL,
            provider_user_id  TEXT NOT NULL,
            conversation_id   UUID NOT NULL,
            last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, channel, provider_user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_channel_conversation_last_seen "
        "ON channel_conversation_index(workspace_id, channel, last_seen_at DESC)"
    )
    op.execute("ALTER TABLE channel_conversation_index ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE channel_conversation_index FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY channel_conversation_index_workspace_isolation
        ON channel_conversation_index
        USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        WITH CHECK (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS channel_conversation_index")
