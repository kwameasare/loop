"""cp_0010 align agents table with the in-memory AgentRecord [P0.2].

cp_0001 sketched the ``agents`` table as ``(id, workspace_id, slug,
display_name, current_version_id UUID, ...)`` against an older spec
that assumed every agent would have a referenced agent_versions row.
The cp-api today ships :class:`AgentRegistry` (process-local), whose
:class:`AgentRecord` Pydantic model is ``(id, workspace_id, name,
slug, description, active_version: int | None, created_at,
archived_at)``.

This migration aligns the schema so :class:`PostgresAgentRegistry`
can be a drop-in replacement:

* Rename ``display_name`` → ``name`` (the in-memory model uses
  ``name``).
* Add ``description TEXT NOT NULL DEFAULT ''`` so the column matches
  the Pydantic model. Default is ``''`` to keep the migration
  backward-compatible against the rare cp_0001 dev DB that already
  has agent rows; the in-memory ``AgentCreate`` model also defaults
  ``description`` to the empty string.

The ``current_version_id`` column is left in place — it's a richer
model the in-memory registry doesn't use today but a future agent-
versions service will. :class:`PostgresAgentRegistry` reads and
writes it as opaque (always NULL) until the version-management code
lands.

Revision ID: cp_0011_agents_align
Revises: cp_0010_audit_log_no_ws_fk
Create Date: 2027-06-18 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0011_agents_align"
down_revision: str | Sequence[str] | None = "cp_0010_audit_log_no_ws_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE agents RENAME COLUMN display_name TO name")
    op.execute(
        "ALTER TABLE agents ADD COLUMN description TEXT NOT NULL DEFAULT ''"
    )
    # Drop the default so future INSERTs that forget to supply
    # ``description`` raise NOT NULL violation (matches the cp_0008
    # ``created_by`` pattern).
    op.execute("ALTER TABLE agents ALTER COLUMN description DROP DEFAULT")


def downgrade() -> None:
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE agents RENAME COLUMN name TO display_name")
