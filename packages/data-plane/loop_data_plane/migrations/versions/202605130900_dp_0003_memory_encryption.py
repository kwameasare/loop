"""dp_0003_memory_encryption: encrypted memory payload columns

Revision ID: dp_0003_memory_encryption
Revises: dp_0002_kb
Create Date: 2026-05-13 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0003_memory_encryption"
down_revision: str | Sequence[str] | None = "dp_0002_kb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("memory_user", "memory_bot"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN value_ciphertext BYTEA NOT NULL DEFAULT '\\x'::bytea")
        op.execute(f"ALTER TABLE {table} ADD COLUMN nonce BYTEA NOT NULL DEFAULT '\\x'::bytea")
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN algorithm TEXT NOT NULL "
            "DEFAULT 'loop.memory.aesgcm.v1'"
        )
        op.execute(f"ALTER TABLE {table} DROP COLUMN value_json")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN value_ciphertext DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN nonce DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN algorithm DROP DEFAULT")


def downgrade() -> None:
    for table in ("memory_user", "memory_bot"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN value_json JSONB NOT NULL DEFAULT '{{}}'::jsonb")
        op.execute(f"ALTER TABLE {table} DROP COLUMN algorithm")
        op.execute(f"ALTER TABLE {table} DROP COLUMN nonce")
        op.execute(f"ALTER TABLE {table} DROP COLUMN value_ciphertext")
