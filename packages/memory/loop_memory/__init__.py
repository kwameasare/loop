"""Loop memory tiers.

This package implements the **persistent** memory tiers from
``loop_implementation/data/SCHEMA.md`` §3.2 plus the **session** tier
backed by Redis (§5):

* User memory  -- ``memory_user`` Postgres table, scoped per
  ``(workspace_id, agent_id, user_id, key)``.
* Bot memory   -- ``memory_bot`` Postgres table, scoped per
  ``(workspace_id, agent_id, key)``.
* Session memory -- Redis hash at
  ``loop:session:{conversation_id}:{key}`` with a 24h TTL by default.

Two stores expose orthogonal protocols (``UserMemoryStore`` and
``SessionMemoryStore``) so the runtime can swap drivers in tests
without pulling Postgres/Redis. In-memory implementations live in
``loop_memory.inmemory``; the production adapters live in
``loop_memory.postgres`` and ``loop_memory.redis_session``.

Episodic memory (Qdrant + Postgres long-form recall) is intentionally
out of scope here -- it lands with the KB engine in S015.
"""

from loop_memory.inmemory import InMemorySessionMemoryStore, InMemoryUserMemoryStore
from loop_memory.models import MemoryEntry, MemoryScope, SessionEntry
from loop_memory.postgres import PostgresUserMemoryStore
from loop_memory.redis_session import RedisSessionMemoryStore
from loop_memory.stores import (
    MemoryNotFoundError,
    SessionMemoryStore,
    UserMemoryStore,
)

__version__ = "0.1.0"

__all__ = [
    "InMemorySessionMemoryStore",
    "InMemoryUserMemoryStore",
    "MemoryEntry",
    "MemoryNotFoundError",
    "MemoryScope",
    "PostgresUserMemoryStore",
    "RedisSessionMemoryStore",
    "SessionEntry",
    "SessionMemoryStore",
    "UserMemoryStore",
    "__version__",
]
