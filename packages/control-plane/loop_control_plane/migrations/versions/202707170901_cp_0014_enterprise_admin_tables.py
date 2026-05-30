"""cp_0014 enterprise_signups + workspace_invites — admin-portal persistence.

Two tables that back the system-admin and enterprise-admin surfaces.
Both were previously held in process-local dicts on
:class:`CpApiState`; surviving a cp-api restart needs Postgres.

* ``enterprise_signups`` — keyed by free-form ``ens_<hex>`` string id.
  Holds the captured intent from the public signup form plus the
  status transition that a system-admin drives (``pending_review`` →
  ``approved``).
* ``workspace_invites`` — keyed by free-form ``inv_<hex>`` string id.
  Holds pending member/admin invites, including the synthetic owner
  invite emitted on enterprise-signup approval. Indexed on
  ``workspace_id`` so the per-workspace invites listing is O(log n).

Both tables are tenant-scoped at the API layer (the routes already
gate with ``authorize_workspace_access(required_role=ADMIN)``) so we
don't enable RLS here — system-admin overview needs to read every
tenant's pending state, and a USING(workspace_id=...) policy would
block that. Compare with ``channel_binding_secrets`` (cp_0013) which
adds RLS because adapter reads are always scoped to a single tenant.

Revision ID: cp_0014_enterprise_admin_tables
Revises: cp_0013_channel_binding_secrets
Create Date: 2027-07-17 09:01:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "cp_0014_enterprise_admin_tables"
down_revision: str | Sequence[str] | None = "cp_0013_channel_binding_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE enterprise_signups (
            id                       TEXT PRIMARY KEY,
            organization_name        TEXT NOT NULL,
            workspace_slug           TEXT NOT NULL,
            admin_name               TEXT NOT NULL,
            admin_email              TEXT NOT NULL,
            company_size             TEXT NOT NULL,
            region                   TEXT NOT NULL,
            primary_use_case         TEXT NOT NULL,
            channel_priorities       TEXT[] NOT NULL DEFAULT '{}',
            compliance_needs         TEXT[] NOT NULL DEFAULT '{}',
            sso_required             BOOLEAN NOT NULL DEFAULT FALSE,
            status                   TEXT NOT NULL DEFAULT 'pending_review'
                                     CHECK (status IN ('pending_review', 'approved', 'rejected')),
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            approved_workspace_id    TEXT,
            approved_by              TEXT,
            admin_invite_id          TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_enterprise_signups_status_created "
        "ON enterprise_signups(status, created_at DESC)"
    )

    op.execute(
        """
        CREATE TABLE workspace_invites (
            id              TEXT PRIMARY KEY,
            workspace_id    UUID NOT NULL,
            email           TEXT NOT NULL,
            role            TEXT NOT NULL,
            full_name       TEXT,
            note            TEXT,
            status          TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at      TIMESTAMPTZ NOT NULL,
            created_by      TEXT NOT NULL,
            invite_url      TEXT NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_workspace_invites_workspace_created "
        "ON workspace_invites(workspace_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_invites CASCADE")
    op.execute("DROP TABLE IF EXISTS enterprise_signups CASCADE")
