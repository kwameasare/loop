"""dp_0002_kb knowledge base tables (S211): kb_documents + kb_chunks

Revision ID: dp_0002_kb
Revises: dp_0001_initial
Create Date: 2026-05-12 04:00:00

Adds the per-tenant KB ingestion tables described in
``loop_implementation/data/SCHEMA.md`` § 3.4. Both tables are
tenanted (``workspace_id NOT NULL``) and ship with the same RLS
predicate as dp_0001 — ``workspace_id = current_setting('loop.workspace_id')::uuid``
— so the kb-engine never sees rows outside the active session
workspace.

The chunks table carries a ``tsvector`` column generated from
``content`` so the BM25 path (S204) can run a parallel ``GIN`` index
without an extra round-trip.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "dp_0002_kb"
down_revision: str | Sequence[str] | None = "dp_0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TENANTED_TABLES = ("kb_documents", "kb_chunks")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE kb_documents (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL,
            agent_id        UUID NOT NULL,
            source_uri      TEXT NOT NULL,
            mime_type       TEXT NOT NULL,
            byte_size       BIGINT NOT NULL CHECK (byte_size >= 0),
            content_hash    TEXT NOT NULL,
            title           TEXT,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            tombstoned_at   TIMESTAMPTZ,
            UNIQUE (workspace_id, agent_id, content_hash)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_kb_documents_ws_agent ON kb_documents(workspace_id, agent_id) "
        "WHERE tombstoned_at IS NULL"
    )

    op.execute(
        """
        CREATE TABLE kb_chunks (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL,
            agent_id        UUID NOT NULL,
            document_id     UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
            ordinal         INT  NOT NULL CHECK (ordinal >= 0),
            content         TEXT NOT NULL,
            content_hash    TEXT NOT NULL,
            token_count     INT  NOT NULL CHECK (token_count >= 0),
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            tsv             tsvector GENERATED ALWAYS AS (
                                to_tsvector('english', content)
                            ) STORED,
            embedded_at     TIMESTAMPTZ,
            UNIQUE (document_id, ordinal)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_kb_chunks_ws_agent ON kb_chunks(workspace_id, agent_id)"
    )
    op.execute(
        "CREATE INDEX idx_kb_chunks_tsv ON kb_chunks USING GIN (tsv)"
    )

    # RLS: same predicate shape as dp_0001.
    for table in _TENANTED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_workspace_isolation ON {table}
            USING (workspace_id = current_setting('loop.workspace_id')::uuid)
            WITH CHECK (workspace_id = current_setting('loop.workspace_id')::uuid)
            """
        )


def downgrade() -> None:
    for table in reversed(_TENANTED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_workspace_isolation ON {table}")
    op.execute("DROP TABLE IF EXISTS kb_chunks")
    op.execute("DROP TABLE IF EXISTS kb_documents")
