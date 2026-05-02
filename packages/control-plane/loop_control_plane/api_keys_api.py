"""HTTP-shaped facade over :class:`ApiKeyService` (S113-S115).

Framework-agnostic: routes map to:

* ``POST   /v1/workspaces/{ws}/api-keys``        -> :meth:`create`  (S113)
* ``GET    /v1/workspaces/{ws}/api-keys``        -> :meth:`list_for_workspace`  (S114)
* ``DELETE /v1/workspaces/{ws}/api-keys/{kid}``  -> :meth:`revoke`  (S115)

Authorisation rules:

* ``create`` and ``revoke`` require the caller to be at least an ``ADMIN``
  in the workspace. (Owners and admins; not plain members.)
* ``list_for_workspace`` requires plain membership.

Plaintext exposure: the only place a key's plaintext is ever surfaced
is :meth:`create`'s response. The list endpoint and the revoke endpoint
deliberately omit it; the stored row only carries a SHA-256 hash. This
preserves the "shown once" guarantee laid down in
``loop_control_plane.api_keys``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from loop_control_plane.api_keys import (
    ApiKey,
    ApiKeyError,
    ApiKeyService,
    IssuedApiKey,
)
from loop_control_plane.audit import (
    AuditContext,
    AuditEventInput,
    AuditLog,
    InMemoryAuditLog,
    audit_log_append,
)
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.workspaces import Role, WorkspaceService


def _serialise(record: ApiKey) -> dict[str, Any]:
    """Serialise an :class:`ApiKey` *without* the secret hash.

    The hash is internal and is never exposed over the wire -- if a
    downstream system ever needs to verify a key it should call
    :meth:`ApiKeyService.verify` with the plaintext.
    """
    return {
        "id": str(record.id),
        "workspace_id": str(record.workspace_id),
        "name": record.name,
        "prefix": record.prefix,
        "created_at": record.created_at.isoformat(),
        "created_by": record.created_by,
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
    }


def _serialise_issued(issued: IssuedApiKey) -> dict[str, Any]:
    body = _serialise(issued.record)
    body["plaintext"] = issued.plaintext  # shown once
    return body


def _require_str(name: str, value: object, *, min_length: int = 1) -> str:
    if not isinstance(value, str) or len(value) < min_length:
        raise ApiKeyError(f"{name} must be a non-empty string")
    return value


@dataclass
class ApiKeyAPI:
    """Facade combining workspace authorisation + key issuance."""

    api_keys: ApiKeyService
    workspaces: WorkspaceService
    audit_log: AuditLog = field(default_factory=InMemoryAuditLog)

    def _audit(
        self,
        *,
        context: AuditContext,
        workspace_id: UUID,
        action: str,
        key_id: UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        audit_log_append(
            self.audit_log,
            AuditEventInput(
                context=context,
                workspace_id=workspace_id,
                action=action,
                resource_type="api_key",
                resource_id=key_id,
                before=before,
                after=after,
            ),
        )

    # -- S113 --------------------------------------------------------------- #
    async def create(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        body: dict[str, Any],
        audit_context: AuditContext | None = None,
    ) -> dict[str, Any]:
        """Issue a new key. Plaintext is included in the response exactly once."""
        await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.ADMIN,
        )
        name = _require_str("name", body.get("name"))
        issued = await self.api_keys.issue(
            workspace_id=workspace_id, name=name, created_by=caller_sub
        )
        body_out = _serialise_issued(issued)
        self._audit(
            context=audit_context or AuditContext.internal(actor=caller_sub),
            workspace_id=workspace_id,
            action="api_key.create",
            key_id=issued.record.id,
            before=None,
            after=_serialise(issued.record),
        )
        return body_out

    # -- S114 --------------------------------------------------------------- #
    async def list_for_workspace(self, *, caller_sub: str, workspace_id: UUID) -> dict[str, Any]:
        await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
        )
        records = await self.api_keys.list_for_workspace(workspace_id)
        records.sort(key=lambda r: r.created_at)
        return {"items": [_serialise(r) for r in records]}

    # -- S115 --------------------------------------------------------------- #
    async def revoke(
        self,
        *,
        caller_sub: str,
        workspace_id: UUID,
        key_id: UUID,
        audit_context: AuditContext | None = None,
    ) -> dict[str, Any]:
        """Soft-delete a key. Idempotent: revoking an already-revoked key is fine."""
        await authorize_workspace_access(
            workspaces=self.workspaces,
            workspace_id=workspace_id,
            user_sub=caller_sub,
            required_role=Role.ADMIN,
        )
        # Cross-tenant guard: a workspace may only revoke its own keys.
        records = await self.api_keys.list_for_workspace(workspace_id)
        before_record = next((r for r in records if r.id == key_id), None)
        if before_record is None:
            raise ApiKeyError(f"unknown key in workspace: {key_id}")
        revoked = await self.api_keys.revoke(key_id=key_id)
        body_out = _serialise(revoked)
        self._audit(
            context=audit_context or AuditContext.internal(actor=caller_sub),
            workspace_id=workspace_id,
            action="api_key.revoke",
            key_id=key_id,
            before=_serialise(before_record),
            after=body_out,
        )
        return body_out


__all__ = ["ApiKeyAPI"]
