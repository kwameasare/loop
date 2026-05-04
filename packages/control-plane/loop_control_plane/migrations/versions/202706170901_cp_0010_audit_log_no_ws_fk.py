"""cp_0009 drop the audit_log → workspaces FK [P0.2 schema fix].

``cp_0005_audit_log`` declared ``audit_log.workspace_id UUID NOT NULL
REFERENCES workspaces(id) ON DELETE CASCADE`` AND a
``RULE no_delete_audit_log AS ON DELETE TO audit_log DO INSTEAD
NOTHING``. These are mutually incompatible: when a workspace is
deleted, Postgres internally fires the ON DELETE CASCADE which
attempts a DELETE on audit_log, which is rewritten by the rule to
"do nothing", which Postgres reports as ``referential integrity
query on "workspaces" from constraint "audit_log_workspace_id_fkey"
on "audit_log" gave unexpected result`` — and the workspace
deletion fails. This is reproducible in any test that calls
:meth:`WorkspaceService.delete` against a Postgres backing.

The append-only design means audit-log entries should outlive their
workspace anyway: an auditor investigating a deletion needs the
"workspace X was deleted at T by U" record to still exist after the
workspace row is gone. The newer ``audit_events`` table
(cp_0005_audit_events) does this correctly — ``workspace_id`` is a
plain UUID column with no FK. Align ``audit_log`` to the same
shape: drop the FK, keep the column.

Revision ID: cp_0010_audit_log_no_ws_fk
Revises: cp_0009_workspace_members_align
Create Date: 2027-06-17 09:01:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0010_audit_log_no_ws_fk"
down_revision: str | Sequence[str] | None = "cp_0009_workspace_members_align"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_workspace_id_fkey"
    )


def downgrade() -> None:
    # Note: restoring the FK with ON DELETE CASCADE re-introduces the
    # cascade-vs-rule incompatibility. The downgrade is provided for
    # alembic completeness; do not apply it on a database that hosts
    # the cp-api or workspace deletes will start failing again.
    op.execute(
        """
        ALTER TABLE audit_log
            ADD CONSTRAINT audit_log_workspace_id_fkey
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        """
    )
