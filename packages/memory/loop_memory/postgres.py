"""Postgres adapter for user/bot memory.

Backs ``memory_user`` and ``memory_bot`` (SCHEMA.md §3.2). Uses
SQLAlchemy 2.0 Core async to keep the dependency surface small (we
don't need ORM mappings for two tables of two value columns).

Tenancy is enforced two ways:

1. Every statement filters by ``workspace_id``.
2. Every operation opens its own transaction and executes
   ``SET LOCAL loop.workspace_id = '<uuid>'`` **before** any data
   query, so the data-plane RLS policy (``FORCE ROW LEVEL SECURITY``
   from dp_0001) double-checks at the database level.

   Without that ``SET LOCAL``, ``current_setting('loop.workspace_id',
   true)`` returns NULL, the policy ``USING (workspace_id = ...)``
   evaluates to NULL → row filtered out, and **every read returns
   zero rows**. Always set the GUC first.

Conflict-on-insert uses ``ON CONFLICT ... DO UPDATE`` so concurrent
writers converge on last-write-wins by ``updated_at``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from loop_memory.models import MemoryEntry, MemoryScope
from loop_memory.stores import MemoryNotFoundError

# `SET LOCAL` must be issued inside an explicit transaction; that's why
# every operation below uses ``engine.begin()`` (never ``engine.connect()``)
# and routes through this helper.
_SET_WS_SQL = text("SET LOCAL loop.workspace_id = :ws")
DEFAULT_MAX_VALUE_BYTES = 64 * 1024
MAX_VALUE_BYTES = int(os.getenv("LOOP_MEMORY_MAX_VALUE_BYTES", str(DEFAULT_MAX_VALUE_BYTES)))
_NONCE_LEN = 12
_ALGORITHM = "loop.memory.aesgcm.v1"
_KEY_ENV = "LOOP_MEMORY_ENCRYPTION_KEY"


async def _enter_workspace(conn: AsyncConnection, workspace_id: UUID) -> None:
    """Bind ``loop.workspace_id`` for the lifetime of this transaction."""
    await conn.execute(_SET_WS_SQL, {"ws": str(workspace_id)})


class MemoryEncryptionError(ValueError):
    """Raised when an encrypted memory payload cannot be opened."""


class PostgresUserMemoryStore:
    """``UserMemoryStore`` implementation against the data-plane Postgres."""

    def __init__(self, engine: AsyncEngine, *, encryption_key: bytes | str | None = None) -> None:
        self._engine = engine
        self._aesgcm = AESGCM(_coerce_key(encryption_key))

    # -- user ---------------------------------------------------------------

    async def get_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry:
        entry = await self.get_user_or_none(
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            key=key,
        )
        if entry is None:
            raise MemoryNotFoundError(
                f"user memory not found: workspace={workspace_id} "
                f"agent={agent_id} user={user_id} key={key!r}"
            )
        return entry

    async def get_user_or_none(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> MemoryEntry | None:
        sql = text(
            """
            SELECT value_ciphertext, nonce, algorithm, updated_at FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag
              AND user_id = :uid AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {"ws": workspace_id, "ag": agent_id, "uid": user_id, "k": key},
                )
            ).first()
        if row is None:
            return None
        value, updated = self._decode_row(
            row,
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
        )
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def set_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
        value: Any,
    ) -> MemoryEntry:
        value_bytes = _serialize_and_check_value(value)
        nonce, ciphertext = self._encrypt_value(
            value_bytes,
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
        )
        sql = text(
            """
            INSERT INTO memory_user
                (workspace_id, agent_id, user_id, key, value_ciphertext, nonce, algorithm, updated_at)
            VALUES (:ws, :ag, :uid, :k, :ciphertext, :nonce, :algorithm, now())
            ON CONFLICT (workspace_id, agent_id, user_id, key)
            DO UPDATE SET value_ciphertext = EXCLUDED.value_ciphertext,
                          nonce = EXCLUDED.nonce,
                          algorithm = EXCLUDED.algorithm,
                          updated_at = EXCLUDED.updated_at
            RETURNING updated_at
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": workspace_id,
                        "ag": agent_id,
                        "uid": user_id,
                        "k": key,
                        "ciphertext": ciphertext,
                        "nonce": nonce,
                        "algorithm": _ALGORITHM,
                    },
                )
            ).first()
        updated = _coerce_dt(row[0]) if row is not None else datetime.now(UTC)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.USER,
            user_id=user_id,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def delete_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
        key: str,
    ) -> bool:
        sql = text(
            """
            DELETE FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag
              AND user_id = :uid AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            result = await conn.execute(
                sql,
                {"ws": workspace_id, "ag": agent_id, "uid": user_id, "k": key},
            )
        return result.rowcount > 0

    async def delete_all_for_user(self, *, workspace_id: UUID, user_id: str) -> int:
        """Delete every memory row for ``user_id`` in one workspace.

        Used by GDPR right-to-erasure workflows. The statement is scoped
        by ``workspace_id`` and also runs under the workspace RLS GUC.
        """

        sql = text(
            """
            DELETE FROM memory_user
            WHERE workspace_id = :ws AND user_id = :uid
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            result = await conn.execute(sql, {"ws": workspace_id, "uid": user_id})
        return int(result.rowcount or 0)

    async def delete_all_for_workspace(self, workspace_id: UUID) -> int:
        """Delete all user and bot memory for a workspace deletion cascade."""

        delete_user_sql = text("DELETE FROM memory_user WHERE workspace_id = :ws")
        delete_bot_sql = text("DELETE FROM memory_bot WHERE workspace_id = :ws")
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            user_result = await conn.execute(delete_user_sql, {"ws": workspace_id})
            bot_result = await conn.execute(delete_bot_sql, {"ws": workspace_id})
        return int(user_result.rowcount or 0) + int(bot_result.rowcount or 0)

    async def list_user(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: str,
    ) -> list[MemoryEntry]:
        sql = text(
            """
            SELECT key, value_ciphertext, nonce, algorithm, updated_at FROM memory_user
            WHERE workspace_id = :ws AND agent_id = :ag AND user_id = :uid
            ORDER BY key
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            rows = (
                await conn.execute(sql, {"ws": workspace_id, "ag": agent_id, "uid": user_id})
            ).all()
        out: list[MemoryEntry] = []
        for k, ciphertext, nonce, algorithm, updated in rows:
            value = self._decrypt_value(
                ciphertext,
                nonce,
                algorithm,
                workspace_id=workspace_id,
                agent_id=agent_id,
                scope=MemoryScope.USER,
                user_id=user_id,
                key=k,
            )
            out.append(
                MemoryEntry(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    scope=MemoryScope.USER,
                    user_id=user_id,
                    key=k,
                    value=value,
                    updated_at=_coerce_dt(updated),
                )
            )
        return out

    # -- bot ----------------------------------------------------------------

    async def get_bot(self, *, workspace_id: UUID, agent_id: UUID, key: str) -> MemoryEntry:
        entry = await self.get_bot_or_none(workspace_id=workspace_id, agent_id=agent_id, key=key)
        if entry is None:
            raise MemoryNotFoundError(
                f"bot memory not found: workspace={workspace_id} agent={agent_id} key={key!r}"
            )
        return entry

    async def get_bot_or_none(
        self, *, workspace_id: UUID, agent_id: UUID, key: str
    ) -> MemoryEntry | None:
        sql = text(
            """
            SELECT value_ciphertext, nonce, algorithm, updated_at FROM memory_bot
            WHERE workspace_id = :ws AND agent_id = :ag AND key = :k
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (await conn.execute(sql, {"ws": workspace_id, "ag": agent_id, "k": key})).first()
        if row is None:
            return None
        value, updated = self._decode_row(
            row,
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            user_id=None,
            key=key,
        )
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            key=key,
            value=value,
            updated_at=updated,
        )

    async def set_bot(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        key: str,
        value: Any,
    ) -> MemoryEntry:
        value_bytes = _serialize_and_check_value(value)
        nonce, ciphertext = self._encrypt_value(
            value_bytes,
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            user_id=None,
            key=key,
        )
        sql = text(
            """
            INSERT INTO memory_bot
                (workspace_id, agent_id, key, value_ciphertext, nonce, algorithm, updated_at)
            VALUES (:ws, :ag, :k, :ciphertext, :nonce, :algorithm, now())
            ON CONFLICT (workspace_id, agent_id, key)
            DO UPDATE SET value_ciphertext = EXCLUDED.value_ciphertext,
                          nonce = EXCLUDED.nonce,
                          algorithm = EXCLUDED.algorithm,
                          updated_at = EXCLUDED.updated_at
            RETURNING updated_at
            """
        )
        async with self._engine.begin() as conn:
            await _enter_workspace(conn, workspace_id)
            row = (
                await conn.execute(
                    sql,
                    {
                        "ws": workspace_id,
                        "ag": agent_id,
                        "k": key,
                        "ciphertext": ciphertext,
                        "nonce": nonce,
                        "algorithm": _ALGORITHM,
                    },
                )
            ).first()
        updated = _coerce_dt(row[0]) if row is not None else datetime.now(UTC)
        return MemoryEntry(
            workspace_id=workspace_id,
            agent_id=agent_id,
            scope=MemoryScope.BOT,
            key=key,
            value=value,
            updated_at=updated,
        )

    def _encrypt_value(
        self,
        plaintext: bytes,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        scope: MemoryScope,
        user_id: str | None,
        key: str,
    ) -> tuple[bytes, bytes]:
        nonce = os.urandom(_NONCE_LEN)
        ciphertext = self._aesgcm.encrypt(
            nonce,
            plaintext,
            _aad(workspace_id=workspace_id, agent_id=agent_id, scope=scope, user_id=user_id, key=key),
        )
        return nonce, ciphertext

    def _decode_row(
        self,
        row: Any,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        scope: MemoryScope,
        user_id: str | None,
        key: str,
    ) -> tuple[Any, datetime]:
        ciphertext, nonce, algorithm, updated = row[0], row[1], row[2], row[3]
        return (
            self._decrypt_value(
                ciphertext,
                nonce,
                algorithm,
                workspace_id=workspace_id,
                agent_id=agent_id,
                scope=scope,
                user_id=user_id,
                key=key,
            ),
            _coerce_dt(updated),
        )

    def _decrypt_value(
        self,
        ciphertext: bytes,
        nonce: bytes,
        algorithm: str,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        scope: MemoryScope,
        user_id: str | None,
        key: str,
    ) -> Any:
        if algorithm != _ALGORITHM:
            raise MemoryEncryptionError("unsupported memory encryption algorithm")
        try:
            plaintext = self._aesgcm.decrypt(
                bytes(nonce),
                bytes(ciphertext),
                _aad(workspace_id=workspace_id, agent_id=agent_id, scope=scope, user_id=user_id, key=key),
            )
        except InvalidTag as exc:
            raise MemoryEncryptionError("memory payload authentication failed") from exc
        return json.loads(plaintext.decode("utf-8"))


def _serialize_and_check_value(value: Any) -> bytes:
    encoded = json.dumps(value, default=str, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_VALUE_BYTES:
        raise MemoryError("value exceeds 64 KiB")
    return encoded


def _coerce_key(value: bytes | str | None) -> bytes:
    raw = value if value is not None else os.getenv(_KEY_ENV)
    if raw is None:
        raise MemoryEncryptionError(f"{_KEY_ENV} is required for Postgres memory encryption")
    if isinstance(raw, str):
        raw = _decode_key_string(raw)
    if len(raw) in (16, 24, 32):
        return raw
    return hashlib.sha256(raw).digest()


def _decode_key_string(value: str) -> bytes:
    stripped = value.strip()
    if stripped.startswith("base64:"):
        return base64.b64decode(stripped.removeprefix("base64:"))
    if stripped.startswith("hex:"):
        return bytes.fromhex(stripped.removeprefix("hex:"))
    try:
        return base64.b64decode(stripped, validate=True)
    except Exception:
        return stripped.encode("utf-8")


def _aad(
    *,
    workspace_id: UUID,
    agent_id: UUID,
    scope: MemoryScope,
    user_id: str | None,
    key: str,
) -> bytes:
    user = user_id if user_id is not None else "-"
    return f"loop.memory:{workspace_id}:{agent_id}:{scope.value}:{user}:{key}".encode()


def _decode_value(raw: Any) -> Any:
    """JSONB columns may surface as already-decoded objects (psycopg)
    or as raw JSON strings (asyncpg, depending on type codec)."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(UTC)


__all__ = [
    "MAX_VALUE_BYTES",
    "MemoryEncryptionError",
    "PostgresUserMemoryStore",
]
