"""cp_0015 agent_intakes — durable agent creation evidence.

The Studio create-agent flow redirects to
``/agents/{agent_id}?intake={intake_id}`` so the Workbench can show exactly
what was created: Commitment Document, channel bindings, mock tools, starter
evals, candidate knowledge, and the jobs that produced them. Keeping this in
process memory makes the landing evidence disappear on cp-api restart.

Store the full typed intake payload as JSONB and index by workspace so the
route contract stays stable while the implementation becomes durable.

Revision ID: cp_0015_agent_intakes
Revises: cp_0014_enterprise_admin_tables
Create Date: 2027-07-17 09:02:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0015_agent_intakes"
down_revision: str | Sequence[str] | None = "cp_0014_enterprise_admin_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE agent_intakes (
            id              TEXT PRIMARY KEY,
            workspace_id    UUID NOT NULL,
            agent_id        UUID NOT NULL,
            state           TEXT NOT NULL,
            payload         JSONB NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_agent_intakes_workspace_updated "
        "ON agent_intakes(workspace_id, updated_at DESC)"
    )
    op.execute("CREATE INDEX idx_agent_intakes_agent ON agent_intakes(agent_id, updated_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_intakes CASCADE")
