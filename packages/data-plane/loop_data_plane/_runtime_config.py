"""Configuration helpers for the dp-runtime FastAPI app."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

from loop_gateway.client import GatewayClient
from loop_gateway.providers import AnthropicProvider, OpenAIProvider

__all__ = [
    "build_gateway",
    "default_agent_model",
    "env",
    "package_version",
    "runtime_build_time",
    "runtime_commit_sha",
    "runtime_version",
]


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def package_version() -> str:
    try:
        return version("loop-data-plane")
    except PackageNotFoundError:
        return "0.1.0"


def runtime_version() -> str:
    return env("LOOP_DP_VERSION", package_version())


def runtime_commit_sha() -> str:
    return env("LOOP_DP_COMMIT_SHA", "0000000-local")


def runtime_build_time() -> str:
    return env("LOOP_DP_BUILD_TIME", datetime.now(UTC).isoformat())


def default_agent_model() -> str:
    """Pick the default model the runtime should use when an agent didn't specify.

    Layered resolution so the runtime keeps working in every environment:

    1. ``LOOP_DP_DEFAULT_MODEL`` env override — operators can pin a
       specific model (e.g. ``gpt-4o-mini`` or ``claude-3-5-haiku-latest``)
       in production where a stale catalog would be worse than a pinned
       name. This wins unconditionally when set.
    2. Live discovery via :func:`loop_gateway.model_catalog.default_model`.
       Hits the vendor's ``/v1/models`` endpoint, caches the result for
       24h on disk, and picks the cheapest current chat model. Survives
       the provider deprecating any specific model id.
    3. Bundled fallback (inside the catalog) if discovery fails — keeps
       the runtime usable when offline / without API keys.

    Default vendor is OpenAI; flip to Anthropic by setting
    ``LOOP_DP_DEFAULT_VENDOR=anthropic``. Profile (cost vs quality)
    via ``LOOP_DP_DEFAULT_PROFILE`` ∈ {cheap, balanced, best}.
    """
    pinned = env("LOOP_DP_DEFAULT_MODEL").strip()
    if pinned:
        return pinned

    from loop_gateway.model_catalog import default_model

    vendor_raw = env("LOOP_DP_DEFAULT_VENDOR", "openai").strip().lower()
    profile_raw = env("LOOP_DP_DEFAULT_PROFILE", "cheap").strip().lower()
    vendor = vendor_raw if vendor_raw in ("openai", "anthropic") else "openai"
    profile = profile_raw if profile_raw in ("cheap", "balanced", "best") else "cheap"
    return default_model(vendor, profile=profile)  # type: ignore[arg-type]


def _optional(name: str) -> str | None:
    value = env(name).strip()
    return value or None


def build_gateway() -> GatewayClient:
    ttl = float(env("LOOP_GATEWAY_REQUEST_ID_TTL_SECONDS", "600"))
    return GatewayClient(
        providers=[
            OpenAIProvider(base_url=_optional("LOOP_DP_OPENAI_BASE_URL")),
            AnthropicProvider(base_url=_optional("LOOP_DP_ANTHROPIC_BASE_URL")),
        ],
        ttl_seconds=ttl,
    )
