"""Shared scratchpad memory across sub-agents (S406).

Multi-agent runs need a place to stash intermediate state that
*parent* and *child* agents both read, while keeping each child's
private notes from leaking to siblings. The :class:`SharedScratchpad`
gives every node a scope keyed by its node-id; it inherits writes
made under the ``"shared"`` scope (visible to all) and the parent
chain.

This is the in-process implementation. The remote variant pushes
each ``set`` through a Redis Lua script for atomic CAS; the surface
is identical so callers can swap backends via DI.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = ["ScratchpadError", "SharedScratchpad"]


SHARED_SCOPE = "shared"


class ScratchpadError(KeyError):
    """Lookup against an unknown scope or key."""


@dataclass
class SharedScratchpad:
    """Hierarchical kv store: writes pinned to a scope, reads chain upward.

    Each node gets its own scope; siblings cannot see each other's
    writes — that is the whole point of multi-agent isolation. Use
    :meth:`set_shared` for values the parent wants to broadcast.
    """

    _scopes: dict[str, dict[str, object]] = field(default_factory=dict)
    # parent links — child_scope → parent_scope. Roots map to "" (none).
    _parents: dict[str, str] = field(default_factory=dict)

    def open_scope(self, scope: str, *, parent: str = "") -> None:
        if not scope:
            raise ScratchpadError("scope must be non-empty")
        if scope == SHARED_SCOPE:
            raise ScratchpadError("'shared' is reserved")
        if parent and parent not in self._scopes and parent != SHARED_SCOPE:
            raise ScratchpadError(f"unknown parent scope: {parent!r}")
        self._scopes.setdefault(scope, {})
        self._parents[scope] = parent

    def set(self, scope: str, key: str, value: object) -> None:
        if scope not in self._scopes:
            raise ScratchpadError(f"unknown scope: {scope!r}")
        self._scopes[scope][key] = value

    def set_shared(self, key: str, value: object) -> None:
        self._scopes.setdefault(SHARED_SCOPE, {})[key] = value

    def get(self, scope: str, key: str) -> object:
        if scope not in self._scopes:
            raise ScratchpadError(f"unknown scope: {scope!r}")
        # walk up: own → parents → shared.
        cur: str = scope
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            bucket = self._scopes.get(cur, {})
            if key in bucket:
                return bucket[key]
            cur = self._parents.get(cur, "")
        shared = self._scopes.get(SHARED_SCOPE, {})
        if key in shared:
            return shared[key]
        raise ScratchpadError(f"key {key!r} not visible in scope {scope!r}")

    def view(self, scope: str) -> Mapping[str, object]:
        """Read-only merged view of everything visible in ``scope``."""
        if scope not in self._scopes:
            raise ScratchpadError(f"unknown scope: {scope!r}")
        merged: dict[str, object] = {}
        merged.update(self._scopes.get(SHARED_SCOPE, {}))
        # Walk root → leaf so child overrides parent.
        chain: list[str] = []
        cur: str = scope
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = self._parents.get(cur, "")
        for s in reversed(chain):
            merged.update(self._scopes[s])
        return merged
