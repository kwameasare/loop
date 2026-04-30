"""Tool-result caching (S734).

Some tools are pure functions of their arguments (read-only HTTP GETs,
SQL SELECTs against a snapshot, deterministic library calls). For these
we can short-circuit the sandbox dispatch entirely on a cache hit.

* Opt-in per tool via ``cacheable=True`` in the spec; default is False.
* Cache key includes the workspace_id, tool name, and a sha256 of the
  canonical-JSON-serialised arguments. Workspace scoping is mandatory
  \u2014 cross-tenant cache hits are a P0 isolation bug.
* Per-tool TTL; expired entries are evicted lazily on read.
* Bounded size with LRU eviction so a long-lived process can't OOM.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

DEFAULT_MAX_ENTRIES: int = 4096


@dataclass(frozen=True, slots=True)
class CachePolicy:
    """Per-tool caching policy."""

    cacheable: bool = False
    ttl_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")


def canonical_args_key(arguments: dict[str, Any]) -> str:
    """Stable sha256 over JSON-canonical arguments.

    ``sort_keys=True`` + ``separators=(',', ':')`` keeps the hash stable
    across Python releases. Non-JSON values raise ``TypeError`` (tool
    arguments are JSON-Schema validated upstream so this should never
    happen at runtime).
    """
    raw = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class ResultCache:
    """LRU result cache, bounded + per-workspace + per-tool."""

    def __init__(
        self,
        *,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >=1")
        self._max = max_entries
        self._now = clock
        self._store: OrderedDict[tuple[str, str, str], _Entry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _key(workspace_id: str, tool: str, arguments: dict[str, Any]) -> tuple[str, str, str]:
        return (workspace_id, tool, canonical_args_key(arguments))

    def get(
        self,
        *,
        workspace_id: str,
        tool: str,
        arguments: dict[str, Any],
        policy: CachePolicy,
    ) -> Any | None:
        if not policy.cacheable:
            return None
        key = self._key(workspace_id, tool, arguments)
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if self._now() > entry.expires_at:
            self._store.pop(key, None)
            self.misses += 1
            return None
        self._store.move_to_end(key)
        self.hits += 1
        return entry.value

    def put(
        self,
        *,
        workspace_id: str,
        tool: str,
        arguments: dict[str, Any],
        result: Any,
        policy: CachePolicy,
    ) -> None:
        if not policy.cacheable:
            return
        key = self._key(workspace_id, tool, arguments)
        self._store[key] = _Entry(value=result, expires_at=self._now() + policy.ttl_seconds)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def invalidate_tool(self, *, workspace_id: str, tool: str) -> int:
        """Drop every entry for ``(workspace_id, tool)``. Returns count."""
        keys = [k for k in self._store if k[0] == workspace_id and k[1] == tool]
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    def __len__(self) -> int:
        return len(self._store)


__all__ = [
    "DEFAULT_MAX_ENTRIES",
    "CachePolicy",
    "ResultCache",
    "canonical_args_key",
]
