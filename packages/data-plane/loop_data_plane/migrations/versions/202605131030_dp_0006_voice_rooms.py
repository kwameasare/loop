"""dp_0006_voice_rooms: persistent LiveKit room state

Revision ID: dp_0006_voice_rooms
Revises: dp_0005_channel_conversation_index
Create Date: 2026-05-13 10:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0006_voice_rooms"
down_revision: str | Sequence[str] | None = "dp_0005_channel_conversation_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE voice_rooms (
            workspace_id       UUID NOT NULL,
            room_id            TEXT PRIMARY KEY,
            agent_id           UUID NOT NULL,
            livekit_room_name  TEXT NOT NULL UNIQUE,
            started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at           TIMESTAMPTZ,
            ttl_seconds        INT NOT NULL CHECK (ttl_seconds > 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_voice_rooms_workspace_started "
        "ON voice_rooms(workspace_id, started_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS voice_rooms")
