"""Bring-Your-Own-Credentials (BYOC) channel secret store.

Enterprise admins paste their Twilio / Meta / Slack / etc. credentials
in the studio's channel-binding form. Loop never originates the
provider account — the customer brings their own WhatsApp Business
account, their own Twilio Number, their own Slack OAuth app.

This module stores the pasted values encrypted at rest. The wire
format on disk is a Fernet token (AES-128-CBC + HMAC-SHA256, with
versioning + IV baked in by ``cryptography.fernet``). The key comes
from ``LOOP_CP_BYOC_KEY`` env var; production deploys wrap that key
with KMS (see ``aws_backends.py`` / ``vault_transit.py``).

Decryption only happens inside the channel adapter at send/receive
time. The studio never reads the plaintext back — it can only confirm
that credentials are set (and rotate them).

For local-dev the in-memory store is sufficient. Postgres-backed
persistence lands in a follow-up migration.

The store is keyed by ``(agent_id, channel_type)`` because the
existing ``ChannelBindingRegistry`` keys bindings that way — one
binding per channel per agent.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "BYOCSecretError",
    "BYOCSecretRecord",
    "BYOCSecretService",
    "PostgresBYOCSecretService",
    "build_byoc_secret_service",
]


class BYOCSecretError(ValueError):
    """Raised when BYOC encryption/decryption fails or the requested
    secret doesn't exist."""


class BYOCSecretRecord(BaseModel):
    """A binding's encrypted credentials. The studio receives this
    serialised form; ``ciphertext`` is never exposed in API responses."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    workspace_id: UUID
    agent_id: UUID
    channel_type: str = Field(min_length=1, max_length=32)
    provider: str = Field(min_length=1, max_length=64)
    # Set at create-time. ``rotated_at`` flips when the operator
    # uploads a new value for the same (agent, channel_type) pair.
    created_at: datetime
    rotated_at: datetime | None
    # Opaque to callers — we expose the iso-format ``rotated_at``
    # timestamp as proof a value exists, not the bytes themselves.
    ciphertext: bytes


def _resolve_key() -> bytes:
    """Read the Fernet key from env. Auto-generates a local dev key if
    none is set so cp boots without ceremony. Production env must set
    ``LOOP_CP_BYOC_KEY`` (44 url-safe base64 bytes)."""
    raw = os.environ.get("LOOP_CP_BYOC_KEY")
    if raw:
        try:
            Fernet(raw.encode("ascii"))
            return raw.encode("ascii")
        except (ValueError, Exception) as exc:  # noqa: BLE001
            raise BYOCSecretError(
                f"LOOP_CP_BYOC_KEY is not a valid Fernet key: {exc}"
            ) from exc
    # No env value: derive a per-process key. We don't persist it
    # because losing it on restart is acceptable for local dev
    # (operator re-uploads credentials).
    return base64.urlsafe_b64encode(os.urandom(32))


class BYOCSecretService:
    """In-memory BYOC secret store. Production swaps in a
    Postgres-backed implementation against the (forthcoming)
    ``channel_binding_secrets`` table.
    """

    def __init__(self, *, key: bytes | None = None) -> None:
        self._fernet = Fernet(key or _resolve_key())
        self._records: dict[tuple[UUID, str], BYOCSecretRecord] = {}
        self._lock = asyncio.Lock()

    async def put(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        channel_type: str,
        provider: str,
        values: dict[str, Any],
    ) -> BYOCSecretRecord:
        """Encrypt + store ``values`` for one (agent, channel) pair.
        Replaces any previous value (rotation)."""
        payload = json.dumps(values, ensure_ascii=True, sort_keys=True).encode(
            "utf-8"
        )
        ciphertext = self._fernet.encrypt(payload)
        async with self._lock:
            key = (agent_id, channel_type)
            previous = self._records.get(key)
            now = datetime.now(UTC)
            record = BYOCSecretRecord(
                workspace_id=workspace_id,
                agent_id=agent_id,
                channel_type=channel_type,
                provider=provider,
                created_at=previous.created_at if previous else now,
                rotated_at=now if previous else None,
                ciphertext=ciphertext,
            )
            self._records[key] = record
            return record

    async def status(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any] | None:
        """Public read for the studio. Confirms a value exists +
        returns timestamps, never the plaintext."""
        async with self._lock:
            record = self._records.get((agent_id, channel_type))
        if record is None:
            return None
        return {
            "agent_id": str(record.agent_id),
            "workspace_id": str(record.workspace_id),
            "channel_type": record.channel_type,
            "provider": record.provider,
            "created_at": record.created_at.isoformat(),
            "rotated_at": (
                record.rotated_at.isoformat() if record.rotated_at else None
            ),
            "has_value": True,
        }

    async def reveal_for_adapter(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any]:
        """Decrypt + return values. Only the channel adapter calls
        this at runtime. Raises ``BYOCSecretError`` if no value or
        the key has changed since encryption."""
        async with self._lock:
            record = self._records.get((agent_id, channel_type))
        if record is None:
            raise BYOCSecretError(
                f"no credentials uploaded for agent {agent_id} channel {channel_type}"
            )
        try:
            payload = self._fernet.decrypt(record.ciphertext)
        except InvalidToken as exc:
            raise BYOCSecretError(
                "byoc key changed since these credentials were uploaded; "
                "operator must re-upload"
            ) from exc
        return json.loads(payload.decode("utf-8"))

    async def delete(self, *, agent_id: UUID, channel_type: str) -> bool:
        async with self._lock:
            return self._records.pop((agent_id, channel_type), None) is not None


# ---------------------------------------------------------------------------
# Postgres-backed store
# ---------------------------------------------------------------------------


class PostgresBYOCSecretService:
    """Postgres-backed BYOC secret store — drop-in for
    :class:`BYOCSecretService`.

    Same async surface (``put / status / reveal_for_adapter / delete``)
    and same return shapes. Encryption stays inside this process —
    plaintext never leaves the cp-api boundary, and the row's
    ``ciphertext`` column holds Fernet tokens just like the in-memory
    record.

    RLS is enabled on ``channel_binding_secrets`` (see
    ``cp_0013_channel_binding_secrets``). Every read/write sets the
    ``app.workspace_id`` GUC inside the same transaction so the
    tenant-isolation policy admits it.

    Wraps an :class:`~sqlalchemy.ext.asyncio.AsyncEngine` because the
    BYOC API is async end-to-end (the route handler awaits).
    """

    def __init__(self, engine: Any, *, key: bytes | None = None) -> None:
        self._engine = engine
        self._fernet = Fernet(key or _resolve_key())

    @classmethod
    def from_url(
        cls,
        database_url: str,
        *,
        key: bytes | None = None,
        echo: bool = False,
    ) -> PostgresBYOCSecretService:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            database_url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        return cls(engine, key=key)

    async def put(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        channel_type: str,
        provider: str,
        values: dict[str, Any],
    ) -> BYOCSecretRecord:
        from sqlalchemy import text

        payload = json.dumps(values, ensure_ascii=True, sort_keys=True).encode(
            "utf-8"
        )
        ciphertext = self._fernet.encrypt(payload)
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.workspace_id', :ws, true)"),
                {"ws": str(workspace_id)},
            )
            # UPSERT: rotation bumps ``rotated_at``, first insert leaves
            # it NULL. ``created_at`` is preserved across rotations.
            result = await conn.execute(
                text(
                    """
                    INSERT INTO channel_binding_secrets (
                        agent_id, channel_type, workspace_id,
                        provider, created_at, rotated_at, ciphertext
                    ) VALUES (
                        :agent_id, :channel_type, :workspace_id,
                        :provider, :created_at, NULL, :ciphertext
                    )
                    ON CONFLICT (agent_id, channel_type) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        rotated_at = :rotated_at,
                        ciphertext = EXCLUDED.ciphertext,
                        workspace_id = EXCLUDED.workspace_id
                    RETURNING created_at, rotated_at
                    """
                ),
                {
                    "agent_id": agent_id,
                    "channel_type": channel_type,
                    "workspace_id": workspace_id,
                    "provider": provider,
                    "created_at": now,
                    "rotated_at": now,
                    "ciphertext": ciphertext,
                },
            )
            row = result.one()
        return BYOCSecretRecord(
            workspace_id=workspace_id,
            agent_id=agent_id,
            channel_type=channel_type,
            provider=provider,
            created_at=row[0],
            rotated_at=row[1],
            ciphertext=ciphertext,
        )

    async def status(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any] | None:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            # No GUC set here — the studio status read needs to find
            # the row even without a workspace context. RLS on this
            # path would force every reader to know the workspace
            # first; instead we rely on the route's authorize check.
            await conn.execute(
                text("SELECT set_config('app.workspace_id', '', true)"),
            )
            result = await conn.execute(
                text(
                    """
                    SELECT workspace_id, provider, created_at, rotated_at
                    FROM channel_binding_secrets
                    WHERE agent_id = :agent_id
                      AND channel_type = :channel_type
                    """
                ),
                {"agent_id": agent_id, "channel_type": channel_type},
            )
            row = result.first()
        if row is None:
            return None
        return {
            "agent_id": str(agent_id),
            "workspace_id": str(row[0]),
            "channel_type": channel_type,
            "provider": row[1],
            "created_at": row[2].isoformat(),
            "rotated_at": row[3].isoformat() if row[3] else None,
            "has_value": True,
        }

    async def reveal_for_adapter(
        self, *, agent_id: UUID, channel_type: str
    ) -> dict[str, Any]:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.workspace_id', '', true)"),
            )
            result = await conn.execute(
                text(
                    """
                    SELECT ciphertext
                    FROM channel_binding_secrets
                    WHERE agent_id = :agent_id
                      AND channel_type = :channel_type
                    """
                ),
                {"agent_id": agent_id, "channel_type": channel_type},
            )
            row = result.first()
        if row is None:
            raise BYOCSecretError(
                f"no credentials uploaded for agent {agent_id} channel {channel_type}"
            )
        ciphertext: bytes = bytes(row[0])
        try:
            payload = self._fernet.decrypt(ciphertext)
        except InvalidToken as exc:
            raise BYOCSecretError(
                "byoc key changed since these credentials were uploaded; "
                "operator must re-upload"
            ) from exc
        return json.loads(payload.decode("utf-8"))

    async def delete(self, *, agent_id: UUID, channel_type: str) -> bool:
        from sqlalchemy import text

        async with self._engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.workspace_id', '', true)"),
            )
            result = await conn.execute(
                text(
                    """
                    DELETE FROM channel_binding_secrets
                    WHERE agent_id = :agent_id
                      AND channel_type = :channel_type
                    """
                ),
                {"agent_id": agent_id, "channel_type": channel_type},
            )
        return result.rowcount > 0


def build_byoc_secret_service(*, key: bytes | None = None) -> BYOCSecretService:
    """Module-level factory mirroring the rest of cp's app_state_*."""
    return BYOCSecretService(key=key)
