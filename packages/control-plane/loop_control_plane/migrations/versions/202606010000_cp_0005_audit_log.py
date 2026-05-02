"""cp_0005 audit log: append-only audit_log table for write-event immutability.

Revision ID: cp_0005_audit_log
Revises: cp_0004_mcp_marketplace
Create Date: 2026-06-01 00:00:00

Implements the audit & compliance table from SCHEMA.md section 2.2a.
Every cp-api write operation (agent deploy, api_key create/revoke,
workspace mutation, SCIM provision, SSO config change, …) must append
a row here. No UPDATE or DELETE is permitted on this table; the chain of
``previous_hash`` / ``entry_hash`` fields lets an auditor verify the log
has not been tampered with.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0005_audit_log"
down_revision: str | Sequence[str] | None = "cp_0004_mcp_marketplace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_log (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            actor_user_id   UUID REFERENCES users(id),
            action          TEXT NOT NULL,
            resource_type   TEXT NOT NULL,
            resource_id     UUID,
            before_state    JSONB,
            after_state     JSONB,
            client_ip       INET,
            user_agent      TEXT,
            request_id      TEXT,
            previous_hash   TEXT,
            entry_hash      TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_audit_workspace_action "
        "ON audit_log(workspace_id, action, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_resource "
        "ON audit_log(workspace_id, resource_type, resource_id)"
    )
    op.execute(
        "CREATE INDEX idx_audit_actor "
        "ON audit_log(actor_user_id, created_at DESC)"
    )
    # Write-only policy: block UPDATE and DELETE at the database level.
    # The rule fires INSTEAD OF the disallowed operation, discarding it
    # and letting the INSTEAD DO NOTHING variant act as a no-op guard.
    op.execute(
        """
        CREATE RULE no_delete_audit_log AS
            ON DELETE TO audit_log DO INSTEAD NOTHING
        """
    )
    op.execute(
        """
        CREATE RULE no_update_audit_log AS
            ON UPDATE TO audit_log DO INSTEAD NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP RULE IF EXISTS no_update_audit_log ON audit_log")
    op.execute("DROP RULE IF EXISTS no_delete_audit_log ON audit_log")
    op.execute("DROP TABLE IF EXISTS audit_log")
