"""cp_0007 persist redacted audit payloads for SOC2 replay.

Revision ID: cp_0007_audit_event_payloads
Revises: cp_0006_merge_audit_heads
Create Date: 2027-06-15 09:02:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0007_audit_event_payloads"
down_revision: str | Sequence[str] | None = "cp_0006_merge_audit_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_event_payloads (
            payload_hash    BYTEA PRIMARY KEY,
            payload_json    JSONB NOT NULL,
            stored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_audit_event_payloads_stored_at "
        "ON audit_event_payloads(stored_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_event_payloads")
