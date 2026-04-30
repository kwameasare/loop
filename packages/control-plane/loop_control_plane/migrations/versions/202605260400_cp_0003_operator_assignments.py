"""cp_0003 operator assignments: human-in-the-loop hand-offs

Revision ID: cp_0003_operator_assignments
Revises: cp_0001_initial
Create Date: 2026-05-26 04:00:00

When an agent escalates to a human operator (S300 inbox flow), a row
in ``operator_assignments`` records who is currently handling the
conversation and when the hand-off started/ended. RLS enforces
workspace isolation so a query in tenant A cannot see assignments in
tenant B.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0003_operator_assignments"
down_revision: str | Sequence[str] | None = "cp_0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE operator_assignments (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       UUID NOT NULL,
            conversation_id    UUID NOT NULL,
            operator_user_sub  TEXT NOT NULL,
            assigned_by_sub    TEXT NOT NULL,
            started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at           TIMESTAMPTZ,
            ended_reason       TEXT
                                CHECK (ended_reason IS NULL
                                       OR ended_reason IN ('resolved','reassigned','timeout','abandoned')),
            CONSTRAINT operator_assignments_window_valid
                CHECK (ended_at IS NULL OR ended_at >= started_at)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX operator_assignments_active_idx
            ON operator_assignments (workspace_id, conversation_id)
            WHERE ended_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX operator_assignments_operator_idx
            ON operator_assignments (operator_user_sub, started_at DESC)
        """
    )
    # Row-level security: queries scoped by `loop.workspace_id` GUC.
    op.execute("ALTER TABLE operator_assignments ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY operator_assignments_tenant_isolation
            ON operator_assignments
            USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
            WITH CHECK (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS operator_assignments_tenant_isolation ON operator_assignments")
    op.execute("ALTER TABLE operator_assignments DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS operator_assignments_operator_idx")
    op.execute("DROP INDEX IF EXISTS operator_assignments_active_idx")
    op.execute("DROP TABLE operator_assignments")
