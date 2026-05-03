"""cp_0006 merge audit-log and audit-events migration heads.

Revision ID: cp_0006_merge_audit_heads
Revises: cp_0005_audit_log, cp_0005_audit_events
Create Date: 2027-06-15 09:01:00
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "cp_0006_merge_audit_heads"
down_revision: str | Sequence[str] | None = (
    "cp_0005_audit_log",
    "cp_0005_audit_events",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
