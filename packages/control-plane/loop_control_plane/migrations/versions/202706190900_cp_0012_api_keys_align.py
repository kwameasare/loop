"""cp_0011 align api_keys with the in-memory ApiKey model [P0.2].

Three column-level mismatches between cp_0001's ``api_keys`` and
:class:`~loop_control_plane.api_keys.ApiKey` that
:class:`PostgresApiKeyService` needs resolved before it can be a
drop-in replacement:

1. ``hash BYTEA`` → ``hash TEXT``. The in-memory model stores the
   sha256 hex string directly (``Field(min_length=64,
   max_length=64)``); BYTEA would force every read/write to
   encode/decode hex, which is fine but obscures the column for
   ad-hoc DBA queries.
2. ``created_by UUID REFERENCES users(id)`` → ``created_by TEXT``.
   Same gap as cp_0008 fixed for ``workspace_members``: the cp-api
   threads an Auth0 ``sub`` string through every call-site and
   never writes a ``users`` row, so a UUID FK breaks the contract.
3. RLS bypass for verification. cp_0001 enables RLS on api_keys
   with ``USING (workspace_id = current_setting('loop.workspace_id',
   true)::uuid)``. But :meth:`ApiKeyService.verify` looks up by
   prefix BEFORE the caller knows which workspace owns the key —
   that's the whole point of verification. RLS-with-workspace-GUC
   makes that lookup impossible. Drop the policy + DISABLE RLS;
   the api_keys table is reachable only via cp-api routes that
   already enforce auth, so RLS at the DB layer adds little
   defence-in-depth here.

Also adds a UNIQUE index on ``prefix`` alone (cp_0001 only had
``UNIQUE(workspace_id, prefix)``) so the verify path's
prefix-only lookup is index-backed and globally unique — matches
the in-memory ``_by_prefix`` dict invariant.

Revision ID: cp_0012_api_keys_align
Revises: cp_0011_agents_align
Create Date: 2027-06-19 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0012_api_keys_align"
down_revision: str | Sequence[str] | None = "cp_0011_agents_align"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop RLS so verify-by-prefix works for any caller.
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON api_keys")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY")

    # 2. hash BYTEA → TEXT. Use ``USING encode(...)`` to convert any
    # existing rows. There are no production rows (cp-api is in-memory
    # in production today), but the USING clause keeps the migration
    # safe for dev databases that have test data.
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN hash TYPE TEXT USING encode(hash, 'hex')"
    )

    # 3. created_by UUID → TEXT. Drop the FK first; existing UUIDs
    # become their string representation.
    op.execute(
        "ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS api_keys_created_by_fkey"
    )
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN created_by TYPE TEXT USING created_by::text"
    )
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by SET NOT NULL")

    # 4. Globally-unique prefix so verify-by-prefix is O(log n) and
    # matches the in-memory ``_by_prefix`` dict's "every prefix maps
    # to exactly one key" invariant.
    op.execute(
        "CREATE UNIQUE INDEX api_keys_prefix_unique ON api_keys(prefix)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS api_keys_prefix_unique")
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by DROP NOT NULL")
    # Best-effort downgrade — the cast back to UUID will fail if any
    # rows have non-UUID created_by values (they will, in production).
    # The downgrade is provided for alembic completeness only.
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN created_by TYPE UUID USING created_by::uuid"
    )
    op.execute(
        """
        ALTER TABLE api_keys
            ADD CONSTRAINT api_keys_created_by_fkey
            FOREIGN KEY (created_by) REFERENCES users(id)
        """
    )
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN hash TYPE BYTEA USING decode(hash, 'hex')"
    )
    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON api_keys
          USING (workspace_id = current_setting('loop.workspace_id', true)::uuid)
        """
    )
