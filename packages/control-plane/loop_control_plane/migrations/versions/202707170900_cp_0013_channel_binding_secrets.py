"""cp_0013 channel_binding_secrets — BYOC channel credentials at rest.

Enterprise admins paste their Twilio / Meta / Slack / etc. credentials
in the studio's channel-binding form. cp encrypts the values with
Fernet (KMS-wrapped in production) and INSERTs them here. Plaintext
only ever decrypts inside the channel adapter at send/receive time —
the studio confirms presence + rotation timestamp but never reads the
plaintext back.

Keyed by ``(agent_id, channel_type)`` to mirror the existing
``ChannelBindingRegistry`` ("at most one binding per channel per
agent") and the in-memory :class:`BYOCSecretService` map.

Rotation semantics: UPDATE in place on the same PK and bump
``rotated_at``; the channel adapter resolving creds via
:meth:`BYOCSecretService.reveal_for_adapter` will pick up the new
ciphertext on its next read.

RLS: tenant-scoped on ``workspace_id`` so a leaked DB credential can
only see one tenant's secrets — same pattern as ``audit_events`` in
cp_0005.

Revision ID: cp_0013_channel_binding_secrets
Revises: cp_0012_api_keys_align
Create Date: 2027-07-17 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0013_channel_binding_secrets"
down_revision: str | Sequence[str] | None = "cp_0012_api_keys_align"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE channel_binding_secrets (
            agent_id        UUID NOT NULL,
            channel_type    TEXT NOT NULL,
            workspace_id    UUID NOT NULL,
            provider        TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            rotated_at      TIMESTAMPTZ,
            ciphertext      BYTEA NOT NULL,
            PRIMARY KEY (agent_id, channel_type)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_channel_binding_secrets_workspace "
        "ON channel_binding_secrets(workspace_id)"
    )
    # Tenant isolation: a leaked DB credential bound to one tenant's
    # session can only read its own row set. Adapter reads always know
    # the workspace_id, so they set the GUC before SELECT/UPDATE/DELETE.
    op.execute("ALTER TABLE channel_binding_secrets ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON channel_binding_secrets
            USING (workspace_id::text = current_setting('app.workspace_id', true))
            WITH CHECK (workspace_id::text = current_setting('app.workspace_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS channel_binding_secrets CASCADE")
