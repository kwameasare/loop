"""WhatsApp media download + cache (S344).

WhatsApp Cloud API delivers inbound media as an opaque ``media_id``.
The bot must:

1. Resolve ``GET /v18.0/{media_id}`` → JSON ``{url, mime_type, ...}``
2. ``GET <url>`` with the same auth bearer to download the bytes.

Bytes can be huge (audio messages up to 16 MB) so we cache them to a
pluggable object store keyed on ``media_id`` for the duration of the
agent turn. The HTTP client and cache are Protocols so this module
runs deterministically in tests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

DEFAULT_TTL_SECONDS = 15 * 60  # 15 min
MAX_MEDIA_BYTES = 100 * 1024 * 1024  # 100 MB hard cap


class WhatsAppMediaError(RuntimeError):
    """Media resolve / download / cache failure."""


@dataclass(frozen=True, slots=True)
class CachedMedia:
    """Bytes + metadata returned to callers."""

    media_id: str
    bytes_: bytes
    mime_type: str
    fetched_at_ms: int


@runtime_checkable
class HttpClient(Protocol):
    async def get_json(self, url: str, *, headers: dict[str, str]) -> dict[str, object]: ...

    async def get_bytes(self, url: str, *, headers: dict[str, str]) -> bytes: ...


@runtime_checkable
class MediaCache(Protocol):
    async def get(self, key: str) -> CachedMedia | None: ...

    async def put(self, item: CachedMedia, *, ttl_seconds: int) -> None: ...


@dataclass(slots=True)
class InMemoryMediaCache:
    """LRU-ish in-process cache (deterministic, used in tests + dev)."""

    max_entries: int = 64
    _store: dict[str, tuple[CachedMedia, int]] = field(default_factory=dict)

    async def get(self, key: str) -> CachedMedia | None:
        item = self._store.get(key)
        if item is None:
            return None
        cached, expires_at = item
        if expires_at <= int(time.time() * 1000):
            self._store.pop(key, None)
            return None
        # Refresh insertion order so this becomes "most recently used".
        self._store.pop(key)
        self._store[key] = (cached, expires_at)
        return cached

    async def put(self, item: CachedMedia, *, ttl_seconds: int) -> None:
        expires_at = int(time.time() * 1000) + ttl_seconds * 1000
        self._store[item.media_id] = (item, expires_at)
        while len(self._store) > self.max_entries:
            # pop oldest insertion
            oldest = next(iter(self._store))
            self._store.pop(oldest)


@dataclass(slots=True)
class WaMediaDownloader:
    """Resolve + download + cache one media_id at a time."""

    http: HttpClient
    cache: MediaCache
    base_url: str = "https://graph.facebook.com/v18.0"
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    max_bytes: int = MAX_MEDIA_BYTES

    def __post_init__(self) -> None:
        if self.ttl_seconds < 30:
            raise ValueError("ttl_seconds must be >=30")
        if self.max_bytes < 1024:
            raise ValueError("max_bytes must be >=1024")

    async def download(self, *, media_id: str, access_token: str) -> CachedMedia:
        if not media_id:
            raise WhatsAppMediaError("media_id required")
        if not access_token:
            raise WhatsAppMediaError("access_token required")
        cached = await self.cache.get(media_id)
        if cached is not None:
            return cached
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            meta = await self.http.get_json(f"{self.base_url}/{media_id}", headers=headers)
        except Exception as exc:
            raise WhatsAppMediaError(f"resolve failed: {exc}") from exc
        url = meta.get("url")
        mime = meta.get("mime_type")
        if not isinstance(url, str) or not url:
            raise WhatsAppMediaError("missing url in media metadata")
        if not isinstance(mime, str) or not mime:
            raise WhatsAppMediaError("missing mime_type in media metadata")
        try:
            blob = await self.http.get_bytes(url, headers=headers)
        except Exception as exc:
            raise WhatsAppMediaError(f"download failed: {exc}") from exc
        if len(blob) > self.max_bytes:
            raise WhatsAppMediaError(
                f"media exceeds max_bytes ({len(blob)} > {self.max_bytes})"
            )
        item = CachedMedia(
            media_id=media_id,
            bytes_=blob,
            mime_type=mime,
            fetched_at_ms=int(time.time() * 1000),
        )
        await self.cache.put(item, ttl_seconds=self.ttl_seconds)
        return item


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "MAX_MEDIA_BYTES",
    "CachedMedia",
    "HttpClient",
    "InMemoryMediaCache",
    "MediaCache",
    "WaMediaDownloader",
    "WhatsAppMediaError",
]
