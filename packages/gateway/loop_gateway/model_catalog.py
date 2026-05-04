"""Live model catalog for the LLM gateway.

Both OpenAI and Anthropic publish a ``GET /v1/models`` endpoint that
returns the current list of model IDs available to the calling
account. Hard-coding a specific model ID (e.g. ``gpt-4o-mini``) in our
default-picker is a maintenance trap — provider deprecation cycles
break the runtime overnight when the literal stops resolving.

This module fetches the live list, caches it, and picks a sensible
default by name-pattern heuristic. Three layers of defence so the
runtime stays usable in every environment:

1. **In-process cache** — once per process, no repeat fetch on every
   turn. Resolved in :class:`ModelCatalog`.
2. **On-disk cache** — ``~/.cache/loop/models.json`` with a 24h TTL.
   Survives uvicorn restarts, kind-pod recycles, and CI cold-starts
   without paying the network round-trip every time.
3. **Bundled fallback** — :data:`FALLBACK_MODELS` is a known-good
   list of stable family names. Used when the provider call fails
   (no network, no API key, rate limit, the user is offline). The
   runtime keeps working with a slightly-stale default rather than
   raising.

ENV
===

* ``LOOP_DP_DEFAULT_MODEL`` — operator override. Skips discovery
  entirely and uses the literal value. Useful for pinning a specific
  model in production where a stale catalog would be worse than a
  pinned name.
* ``LOOP_GATEWAY_OPENAI_API_KEY`` / ``OPENAI_API_KEY`` — used to
  authenticate the discovery call against OpenAI.
* ``LOOP_GATEWAY_ANTHROPIC_API_KEY`` / ``ANTHROPIC_API_KEY`` — same
  for Anthropic.
* ``LOOP_GATEWAY_MODEL_CATALOG_TTL_SECONDS`` — file-cache TTL (default
  86400 = 24h).
* ``LOOP_GATEWAY_MODEL_CATALOG_PATH`` — override for the on-disk
  cache file. Default ``~/.cache/loop/models.json``.

Selection profile
=================

:meth:`ModelCatalog.pick_default` accepts ``profile`` ∈ {``cheap``,
``balanced``, ``best``}. The runtime uses ``cheap`` by default —
short turns are the common case and we want to default-spend the
operator's budget conservatively. A higher profile is opt-in via
agent config or per-turn metadata.

Pattern ranking (highest → lowest priority within each profile):

* ``cheap``    → ``*-mini`` / ``*-haiku`` / ``*-flash`` / ``*-nano``
* ``balanced`` → ``*-sonnet`` / ``*-4o`` / ``*-pro``
* ``best``     → ``*-opus`` / ``*-5`` / ``*-pro-max`` / ``*-turbo``

Within a tier, ``*-latest`` aliases beat dated IDs (Anthropic ships
those; OpenAI does not). Among dated IDs, the lexicographically
largest suffix wins — provider date-stamp conventions (YYYYMMDD or
YYYY-MM-DD) make string sort = chronological sort.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import httpx

__all__ = [
    "FALLBACK_MODELS",
    "ModelCatalog",
    "ModelInfo",
    "Profile",
    "Vendor",
    "default_model",
    "fetch_anthropic_models",
    "fetch_openai_models",
]

log = logging.getLogger(__name__)


Vendor = Literal["openai", "anthropic"]
Profile = Literal["cheap", "balanced", "best"]


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """One row from a vendor's model list."""

    id: str
    """Provider-specific model identifier (e.g. ``gpt-4o-mini-2024-07-18``)."""

    vendor: Vendor
    """Which vendor advertises this model."""

    created_at: int = 0
    """Unix epoch seconds when the model was published. ``0`` if unknown."""

    display_name: str = ""
    """Human-friendly name; ``""`` if vendor doesn't supply one."""


# --------------------------------------------------------------------------- #
# Bundled fallback (used only when the live list can't be fetched)            #
# --------------------------------------------------------------------------- #
#
# Stable family names that resolve at the provider for at least months at a
# time. The point isn't to be exhaustive — it's to keep the runtime usable
# without network/auth. Refresh this list when a family is fully retired.

FALLBACK_MODELS: dict[Vendor, dict[Profile, list[str]]] = {
    "openai": {
        "cheap": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-3.5-turbo"],
        "balanced": ["gpt-4o", "gpt-4.1", "gpt-4-turbo"],
        "best": ["gpt-4o", "gpt-4.1", "gpt-4-turbo"],
    },
    "anthropic": {
        "cheap": ["claude-3-5-haiku-latest", "claude-3-haiku-20240307"],
        "balanced": ["claude-3-5-sonnet-latest", "claude-3-5-sonnet-20241022"],
        "best": ["claude-3-opus-latest", "claude-3-5-sonnet-latest"],
    },
}


# --------------------------------------------------------------------------- #
# Live discovery                                                              #
# --------------------------------------------------------------------------- #


class _ModelFetcher(Protocol):
    def __call__(self, api_key: str, *, base_url: str | None = None) -> list[ModelInfo]: ...


def fetch_openai_models(
    api_key: str,
    *,
    base_url: str | None = None,
    client: httpx.Client | None = None,
    timeout_seconds: float = 5.0,
) -> list[ModelInfo]:
    """Call OpenAI's ``/v1/models`` and return the parsed list.

    Returns ``[]`` if the call fails for any reason (logged as a
    warning). Callers should treat ``[]`` as "fall back to the bundled
    list."
    """
    url = (base_url or "https://api.openai.com").rstrip("/") + "/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        if client is None:
            with httpx.Client(timeout=timeout_seconds) as c:
                response = c.get(url, headers=headers)
        else:
            response = client.get(url, headers=headers)
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        log.warning("openai model discovery failed: %s", exc)
        return []
    data = response.json()
    rows: list[ModelInfo] = []
    for entry in data.get("data", []):
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        if not isinstance(model_id, str):
            continue
        # Filter to chat-shaped models. OpenAI also lists embeddings,
        # whisper, dall-e — we don't want those as turn defaults.
        if not model_id.startswith(("gpt-", "o1", "o3", "o4")):
            continue
        rows.append(
            ModelInfo(
                id=model_id,
                vendor="openai",
                created_at=int(entry.get("created", 0) or 0),
                display_name=str(entry.get("display_name") or ""),
            )
        )
    return rows


def fetch_anthropic_models(
    api_key: str,
    *,
    base_url: str | None = None,
    client: httpx.Client | None = None,
    timeout_seconds: float = 5.0,
) -> list[ModelInfo]:
    """Call Anthropic's ``/v1/models`` and return the parsed list."""
    url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    try:
        if client is None:
            with httpx.Client(timeout=timeout_seconds) as c:
                response = c.get(url, headers=headers)
        else:
            response = client.get(url, headers=headers)
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        log.warning("anthropic model discovery failed: %s", exc)
        return []
    data = response.json()
    rows: list[ModelInfo] = []
    for entry in data.get("data", []):
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        if not isinstance(model_id, str):
            continue
        if not model_id.startswith("claude-"):
            continue
        # Anthropic ships an ISO 8601 ``created_at`` rather than epoch.
        created_iso = entry.get("created_at") or ""
        epoch = 0
        if isinstance(created_iso, str) and created_iso:
            try:
                from datetime import datetime

                epoch = int(datetime.fromisoformat(created_iso.replace("Z", "+00:00")).timestamp())
            except (ValueError, TypeError):
                pass
        rows.append(
            ModelInfo(
                id=model_id,
                vendor="anthropic",
                created_at=epoch,
                display_name=str(entry.get("display_name") or ""),
            )
        )
    return rows


# --------------------------------------------------------------------------- #
# Selection heuristic                                                         #
# --------------------------------------------------------------------------- #


_PROFILE_PATTERNS: dict[Profile, tuple[str, ...]] = {
    "cheap": ("-mini", "-haiku", "-flash", "-nano"),
    "balanced": ("-sonnet", "-4o", "-pro", "-4.1"),
    "best": ("-opus", "-pro-max", "-turbo", "-5", "o1", "o3"),
}


def _profile_score(model: ModelInfo, profile: Profile) -> tuple[int, int, str]:
    """Lower score == better match for the profile.

    Tier 0: model id contains a profile-pattern AND is a ``-latest`` alias.
    Tier 1: model id contains a profile-pattern.
    Tier 2: doesn't match the profile pattern at all.

    Within a tier we prefer the most recently created model (negate
    ``created_at`` so smaller = newer in the sort). Final tiebreaker is
    lexicographic id descending so `-2024-12-01` beats `-2024-07-18`.
    """
    patterns = _PROFILE_PATTERNS[profile]
    is_latest = "-latest" in model.id
    matches_profile = any(p in model.id for p in patterns)
    if matches_profile and is_latest:
        tier = 0
    elif matches_profile:
        tier = 1
    else:
        tier = 2
    return (tier, -model.created_at, model.id[::-1])


# --------------------------------------------------------------------------- #
# Catalog                                                                     #
# --------------------------------------------------------------------------- #


def _default_cache_path() -> Path:
    override = os.environ.get("LOOP_GATEWAY_MODEL_CATALOG_PATH")
    if override:
        return Path(override)
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / "loop" / "models.json"


def _default_cache_ttl_seconds() -> int:
    raw = os.environ.get("LOOP_GATEWAY_MODEL_CATALOG_TTL_SECONDS")
    if not raw:
        return 86_400  # 24h
    try:
        return max(60, int(raw))
    except ValueError:
        return 86_400


@dataclass
class ModelCatalog:
    """Lazy, cached, fallback-resilient model directory.

    Construct once per process. ``list(vendor)`` returns the cached
    list (fetching if cold, falling back if discovery fails). Use
    ``pick_default(vendor, profile)`` to get a model id ready to pass
    to :class:`~loop_gateway.client.GatewayClient`.
    """

    fetch_openai: _ModelFetcher = fetch_openai_models
    fetch_anthropic: _ModelFetcher = fetch_anthropic_models
    cache_path: Path | None = None
    cache_ttl_seconds: int = 0
    _cache: dict[Vendor, list[ModelInfo]] | None = None
    _cache_loaded_at: int = 0

    def __post_init__(self) -> None:
        if self.cache_path is None:
            self.cache_path = _default_cache_path()
        if self.cache_ttl_seconds <= 0:
            self.cache_ttl_seconds = _default_cache_ttl_seconds()

    # ---- public API -----------------------------------------------------

    def list(self, vendor: Vendor) -> list[ModelInfo]:
        cache = self._get_cache()
        return list(cache.get(vendor, []))

    def pick_default(self, vendor: Vendor, *, profile: Profile = "cheap") -> str:
        models = self.list(vendor)
        if not models:
            return _fallback_pick(vendor, profile)
        ranked = sorted(models, key=lambda m: _profile_score(m, profile))
        return ranked[0].id

    def refresh(self) -> dict[Vendor, list[ModelInfo]]:
        """Force a fresh fetch from each vendor. Updates the disk cache."""
        live = self._fetch_live()
        self._cache = live
        self._cache_loaded_at = int(time.time())
        self._write_disk_cache(live)
        return live

    # ---- internals ------------------------------------------------------

    def _get_cache(self) -> dict[Vendor, list[ModelInfo]]:
        if self._cache is not None:
            return self._cache
        on_disk = self._read_disk_cache()
        if on_disk is not None:
            self._cache = on_disk
            return on_disk
        live = self._fetch_live()
        self._cache = live
        self._cache_loaded_at = int(time.time())
        self._write_disk_cache(live)
        return live

    def _fetch_live(self) -> dict[Vendor, list[ModelInfo]]:
        env = os.environ
        out: dict[Vendor, list[ModelInfo]] = {"openai": [], "anthropic": []}

        openai_key = env.get("LOOP_GATEWAY_OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
        if openai_key:
            try:
                out["openai"] = self.fetch_openai(openai_key)
            except Exception as exc:
                log.warning("openai discovery raised %s; will use fallback", exc)

        anthropic_key = env.get("LOOP_GATEWAY_ANTHROPIC_API_KEY") or env.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                out["anthropic"] = self.fetch_anthropic(anthropic_key)
            except Exception as exc:
                log.warning("anthropic discovery raised %s; will use fallback", exc)

        return out

    def _read_disk_cache(self) -> dict[Vendor, list[ModelInfo]] | None:
        if self.cache_path is None or not self.cache_path.is_file():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("model catalog cache unreadable (%s): %s", self.cache_path, exc)
            return None
        fetched_at = int(payload.get("fetched_at", 0))
        if fetched_at <= 0:
            return None
        if time.time() - fetched_at > self.cache_ttl_seconds:
            return None
        out: dict[Vendor, list[ModelInfo]] = {}
        for vendor, rows in payload.get("models", {}).items():
            if vendor not in ("openai", "anthropic"):
                continue
            parsed: list[ModelInfo] = []
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("id"), str):
                    parsed.append(
                        ModelInfo(
                            id=row["id"],
                            vendor=vendor,
                            created_at=int(row.get("created_at", 0) or 0),
                            display_name=str(row.get("display_name", "") or ""),
                        )
                    )
            out[vendor] = parsed  # type: ignore[index]
        self._cache_loaded_at = fetched_at
        return out

    def _write_disk_cache(self, models: dict[Vendor, list[ModelInfo]]) -> None:
        if self.cache_path is None:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "fetched_at": int(time.time()),
                "models": {
                    vendor: [
                        {
                            "id": m.id,
                            "created_at": m.created_at,
                            "display_name": m.display_name,
                        }
                        for m in rows
                    ]
                    for vendor, rows in models.items()
                },
            }
            self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("model catalog cache write failed (%s): %s", self.cache_path, exc)


# --------------------------------------------------------------------------- #
# Module-level helpers                                                        #
# --------------------------------------------------------------------------- #


def _fallback_pick(vendor: Vendor, profile: Profile) -> str:
    """Used when discovery returned nothing. Always returns a non-empty id."""
    candidates = FALLBACK_MODELS[vendor][profile]
    return candidates[0]


_DEFAULT_CATALOG: ModelCatalog | None = None


def _shared_catalog() -> ModelCatalog:
    global _DEFAULT_CATALOG
    if _DEFAULT_CATALOG is None:
        _DEFAULT_CATALOG = ModelCatalog()
    return _DEFAULT_CATALOG


def default_model(vendor: Vendor = "openai", *, profile: Profile = "cheap") -> str:
    """Convenience accessor: returns the catalog's pick for ``vendor`` at ``profile``.

    Honors ``LOOP_DP_DEFAULT_MODEL`` if set so operators can pin a
    specific model in production where a stale catalog would be worse
    than a pinned name.
    """
    pinned = os.environ.get("LOOP_DP_DEFAULT_MODEL", "").strip()
    if pinned:
        return pinned
    return _shared_catalog().pick_default(vendor, profile=profile)
