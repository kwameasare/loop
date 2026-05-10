"""dp_0007_memory_evidence: trace evidence for durable memory

Revision ID: dp_0007_memory_evidence
Revises: dp_0006_voice_rooms
Create Date: 2026-05-13 10:45:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0007_memory_evidence"
down_revision: str | Sequence[str] | None = "dp_0006_voice_rooms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("memory_user", "memory_bot"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN source_trace TEXT NOT NULL DEFAULT ''")
        op.execute(f"ALTER TABLE {table} ADD COLUMN source_turn_id UUID")
        op.execute(f"ALTER TABLE {table} ADD COLUMN source_span_id TEXT NOT NULL DEFAULT ''")
        op.execute(f"ALTER TABLE {table} ADD COLUMN write_reason TEXT NOT NULL DEFAULT ''")
        op.execute(f"ALTER TABLE {table} ADD COLUMN policy_ref TEXT NOT NULL DEFAULT ''")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN source_trace DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN source_span_id DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN write_reason DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN policy_ref DROP DEFAULT")


def downgrade() -> None:
    for table in ("memory_user", "memory_bot"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN policy_ref")
        op.execute(f"ALTER TABLE {table} DROP COLUMN write_reason")
        op.execute(f"ALTER TABLE {table} DROP COLUMN source_span_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN source_turn_id")
        op.execute(f"ALTER TABLE {table} DROP COLUMN source_trace")
