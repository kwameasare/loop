"""cp_0005 SAML group → role rules table — S617

When a workspace connects an enterprise SAML IdP (Okta / Entra /
Workspace) the operator must declare which IdP groups grant which
Loop workspace roles. The mapping rules live in
``workspace_sso_group_rules``: one row per (workspace, group_name)
declaring the projected role and the order of precedence.

The role-projection logic in ``loop_control_plane.saml.project_role``
consumes the rule set as a tuple of
``(group, role)`` pairs; this table is the persistence layer behind
that tuple and is loaded at SSO config time, not at every assertion.

RLS policy keeps tenants isolated; the Studio enterprise SSO tab
writes rows here when the operator edits the mapping table.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0005_sso_group_rules"
down_revision: str | Sequence[str] | None = "cp_0004_mcp_marketplace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workspace_sso_group_rules (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            group_name   TEXT NOT NULL,
            role         TEXT NOT NULL CHECK (role IN ('owner','admin','editor','operator','viewer')),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by   UUID REFERENCES users(id),
            UNIQUE (workspace_id, group_name)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_sso_group_rules_workspace "
        "ON workspace_sso_group_rules(workspace_id)"
    )
    op.execute("ALTER TABLE workspace_sso_group_rules ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON workspace_sso_group_rules "
        "USING (workspace_id::text = current_setting('app.workspace_id', true))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_sso_group_rules")
