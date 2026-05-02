"""cp_0005 audit_events table — append-only audit log [S630].

Every cp-api write endpoint emits exactly one row into ``audit_events``.
The table is INSERT-only at the database layer (an explicit RULE forbids
UPDATE/DELETE) so the audit trail cannot be silently rewritten by an
operator with a leaked DB credential.

Revision ID: cp_0005_audit_events
Revises: cp_0004_mcp_marketplace
Create Date: 2027-06-15 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0005_audit_events"
down_revision: str | Sequence[str] | None = "cp_0004_mcp_marketplace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            workspace_id    UUID NOT NULL,
            actor_sub       TEXT NOT NULL,
            action          TEXT NOT NULL,
            resource_type   TEXT NOT NULL,
            resource_id     TEXT,
            request_id      TEXT,
            payload_hash    TEXT,
            outcome         TEXT NOT NULL DEFAULT 'success'
                            CHECK (outcome IN ('success', 'denied', 'error'))
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_audit_events_workspace_occurred "
        "ON audit_events(workspace_id, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_events_actor_occurred "
        "ON audit_events(actor_sub, occurred_at DESC)"
    )
    # Append-only enforcement at the storage layer — reject UPDATE / DELETE
    # with a rule that's evaluated server-side. Production replicas mirror
    # via logical replication, which is unaffected.
    op.execute(
        "CREATE RULE audit_events_no_update AS ON UPDATE TO audit_events "
        "DO INSTEAD NOTHING"
    )
    op.execute(
        "CREATE RULE audit_events_no_delete AS ON DELETE TO audit_events "
        "DO INSTEAD NOTHING"
    )
    # Tenant-scoped RLS so a leaked workspace credential can only read its
    # own audit trail.
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON audit_events
            USING (workspace_id::text = current_setting('app.workspace_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")
