"""cp_0007 refresh_tokens table — opaque refresh-token row [P0.2].

The cp-api ``POST /v1/auth/exchange`` and ``/v1/auth/refresh`` routes
have been issuing refresh tokens since P0.4, but the backing store
was always :class:`InMemoryRefreshTokenStore` — restart cp-api and
every active session is silently invalidated. This migration creates
the production ``refresh_tokens`` table that
:class:`PostgresRefreshTokenStore` writes to.

Schema mirrors :class:`RefreshTokenRecord`:

* ``token_hash`` PK — sha256 hex of the opaque token.
* ``user_sub`` — the loop user_id (UUID string) but stored as TEXT
  to keep the column friendly to non-UUID identity providers.
* ``expires_at_ms`` — per-token TTL.
* ``family_id`` — every refresh chain shares a family; reuse-
  detection in ``/v1/auth/refresh`` revokes the entire family on
  replay.
* ``family_expires_at_ms`` — the chain's hard deadline (90 days
  from initial exchange). Once a family is past this, every token
  in it is unusable, even if individual ``expires_at_ms`` haven't
  fired.
* ``revoked_at_ms`` — soft-delete marker. The route distinguishes
  "never existed" (``lookup`` returns ``None``) from "revoked"
  (``lookup`` returns a record with ``revoked_at_ms`` set) so it
  can revoke the entire family on replay.

No RLS — refresh tokens are bound to a user, not a workspace.

Revision ID: cp_0008_refresh_tokens
Revises: cp_0007_audit_event_payloads
Create Date: 2027-06-16 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0008_refresh_tokens"
down_revision: str | Sequence[str] | None = "cp_0007_audit_event_payloads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE refresh_tokens (
            token_hash             TEXT PRIMARY KEY,
            user_sub               TEXT NOT NULL,
            expires_at_ms          BIGINT NOT NULL,
            family_id              TEXT NOT NULL,
            family_expires_at_ms   BIGINT NOT NULL,
            revoked_at_ms          BIGINT,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_refresh_tokens_user_sub ON refresh_tokens(user_sub)")
    op.execute("CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id)")
    op.execute("CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at_ms)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
