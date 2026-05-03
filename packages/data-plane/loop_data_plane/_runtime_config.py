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
    return env("LOOP_DP_DEFAULT_MODEL", "gpt-4o-mini")


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
