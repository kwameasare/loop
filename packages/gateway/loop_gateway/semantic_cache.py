"""Gateway semantic cache (S707, extends S029).

Embed the request prompt, cosine-match against entries seen recently for
the same workspace, replay if similarity \u2265 threshold (default 0.97).

A real deployment hosts the index in Redis; the cache here is an in-process
dict keyed by ``workspace_id`` so the algorithm is the same in tests and
production. Per-workspace namespacing is non-negotiable (HANDBOOK +
SECURITY.md \u2014 we never let one tenant's prompt match another's
response).
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

DEFAULT_THRESHOLD: float = 0.97
DEFAULT_TTL_SECONDS: float = 600.0
DEFAULT_MAX_ENTRIES_PER_WORKSPACE: int = 1024


EmbedFn = Callable[[str], Awaitable[list[float]]]
"""``async fn(text) -> vector``. Output dim must be stable per workspace."""


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity in ``[-1, 1]``. Zero-vectors return 0.0."""
    if len(a) != len(b):
        raise ValueError(f"dim mismatch: {len(a)} vs {len(b)}")
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


@dataclass(frozen=True, slots=True)
class CacheHit:
    response: str
    similarity: float
    age_seconds: float


@dataclass(slots=True)
class _Entry:
    vector: list[float]
    response: str
    inserted_at: float


class SemanticCache:
    """In-process LRU semantic cache with per-workspace namespacing."""

    def __init__(
        self,
        embed: EmbedFn,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES_PER_WORKSPACE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be in (0, 1]")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries < 1:
            raise ValueError("max_entries must be >=1")
        self._embed = embed
        self._threshold = threshold
        self._ttl = ttl_seconds
        self._max = max_entries
        self._now = clock
        self._stores: dict[str, OrderedDict[str, _Entry]] = {}

    async def lookup(self, *, workspace_id: str, prompt: str) -> CacheHit | None:
        store = self._stores.get(workspace_id)
        if not store:
            return None
        self._evict_expired(store)
        if not store:
            return None
        vector = await self._embed(prompt)
        best: tuple[str, float, _Entry] | None = None
        for key, entry in store.items():
            sim = cosine(vector, entry.vector)
            if sim >= self._threshold and (best is None or sim > best[1]):
                best = (key, sim, entry)
        if best is None:
            return None
        key, sim, entry = best
        # LRU touch.
        store.move_to_end(key)
        return CacheHit(
            response=entry.response,
            similarity=sim,
            age_seconds=self._now() - entry.inserted_at,
        )

    async def store(
        self,
        *,
        workspace_id: str,
        prompt: str,
        response: str,
    ) -> None:
        store = self._stores.setdefault(workspace_id, OrderedDict())
        vector = await self._embed(prompt)
        # Use the prompt itself as a stable key. Same prompt overwrites.
        store[prompt] = _Entry(vector=vector, response=response, inserted_at=self._now())
        store.move_to_end(prompt)
        while len(store) > self._max:
            store.popitem(last=False)

    def _evict_expired(self, store: OrderedDict[str, _Entry]) -> None:
        now = self._now()
        expired = [k for k, e in store.items() if now - e.inserted_at > self._ttl]
        for k in expired:
            store.pop(k, None)

    def size(self, workspace_id: str) -> int:
        return len(self._stores.get(workspace_id, ()))


__all__ = [
    "DEFAULT_MAX_ENTRIES_PER_WORKSPACE",
    "DEFAULT_THRESHOLD",
    "DEFAULT_TTL_SECONDS",
    "CacheHit",
    "EmbedFn",
    "SemanticCache",
    "cosine",
]
