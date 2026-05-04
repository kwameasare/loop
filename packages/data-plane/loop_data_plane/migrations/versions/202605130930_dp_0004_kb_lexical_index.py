"""dp_0004_kb_lexical_index: persistent KB lexical search

Revision ID: dp_0004_kb_lexical_index
Revises: dp_0003_memory_encryption
Create Date: 2026-05-13 09:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0004_kb_lexical_index"
down_revision: str | Sequence[str] | None = "dp_0003_memory_encryption"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE kb_lexical_index (
            workspace_id UUID NOT NULL,
            doc_id       UUID NOT NULL,
            terms        TEXT NOT NULL,
            tsv          tsvector GENERATED ALWAYS AS (
                           to_tsvector('english', terms)
                         ) STORED,
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, doc_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_kb_lexical_workspace ON kb_lexical_index(workspace_id)")
    op.execute("CREATE INDEX idx_kb_lexical_tsv ON kb_lexical_index USING GIN (tsv)")
    op.execute("ALTER TABLE kb_lexical_index ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE kb_lexical_index FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY kb_lexical_index_workspace_isolation ON kb_lexical_index
        USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        WITH CHECK (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kb_lexical_index")
