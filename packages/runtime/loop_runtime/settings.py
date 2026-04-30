"""dp-runtime configuration settings (S131).

Pydantic-Settings model that loads ``LOOP_RUNTIME_*`` env vars (plus
``.env`` when present) so the runtime image starts with a single
``Settings()`` call. Field types double as schema docs for
:doc:`engineering/ENV_REFERENCE`.

Keep this dependency-light: no external services are imported here.
The ``Settings`` instance flows down to ``TurnExecutor`` /
``CpApiClient`` at startup.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "load_settings"]


LogFormat = Literal["json", "console"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    """All runtime configuration in one strict pydantic model.

    Fields marked ``SecretStr`` are stripped from ``model_dump()``
    representations so accidental log-of-config never leaks. The
    default values are safe for local development; production deploys
    must override ``cp_api_url`` and ``paseto_key`` via env vars.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOOP_RUNTIME_",
        env_file=None,
        case_sensitive=False,
        extra="forbid",
    )

    service_name: str = Field(default="loop-dp-runtime", min_length=1)
    environment: Literal["dev", "staging", "prod"] = "dev"
    region: str = Field(default="local", min_length=1)
    bind_host: str = Field(default="0.0.0.0")  # noqa: S104 — container port
    bind_port: Annotated[int, Field(ge=1, le=65_535)] = 8080
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "json"
    cp_api_url: HttpUrl = HttpUrl("http://cp-api:8080")
    cp_api_timeout_ms: Annotated[int, Field(ge=100, le=60_000)] = 5_000
    cp_api_cache_ttl_ms: Annotated[int, Field(ge=0, le=600_000)] = 60_000
    paseto_key: SecretStr = SecretStr("dev-only-paseto-key-change-me-32bytes!!")
    turn_default_timeout_ms: Annotated[int, Field(ge=1_000, le=600_000)] = 60_000
    turn_max_concurrent_per_workspace: Annotated[int, Field(ge=1, le=10_000)] = 200
    turn_per_workspace_rps: Annotated[float, Field(gt=0, le=10_000)] = 20.0
    turn_per_agent_rps: Annotated[float, Field(gt=0, le=10_000)] = 10.0
    otel_endpoint: HttpUrl | None = None
    otel_sample_ratio: Annotated[float, Field(ge=0, le=1)] = 1.0


def load_settings(**overrides: object) -> Settings:
    """Return a :class:`Settings` instance with optional in-process overrides.

    Used by tests + the cli to inject specific values without mutating
    the process environment.
    """
    return Settings(**overrides)  # type: ignore[arg-type]
