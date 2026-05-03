"""Control-plane configuration (S101).

A `Settings` object that loads ``LOOP_CP_*`` environment variables (and an
optional ``.env`` file) into a strict, immutable model. Missing required
fields raise at startup so misconfigured services fail fast and obviously,
not silently at the first request.

The class deliberately covers only the values required by the in-process
services that ship today (auth provider, db, redis, structured logging
level). Subsystem-specific knobs (Stripe keys, Slack signing secret, ...)
will arrive in their own module once those subsystems land.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthProvider = Literal["auth0", "keycloak", "local"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    """Control-plane runtime configuration.

    The model is frozen so accidental mutation by a request handler raises
    a ``TypeError`` instead of silently leaking state across requests.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOOP_CP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
        case_sensitive=False,
    )

    db_url: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)
    auth_provider: AuthProvider = "auth0"
    auth_issuer: str = Field(default="https://loop.local/", min_length=1)
    auth_audience: str = Field(default="loop-cp", min_length=1)
    local_jwt_secret: str | None = Field(default=None, min_length=1)
    paseto_local_key: str | None = Field(default=None, min_length=32)
    log_level: LogLevel = "INFO"
    region: str = Field(default="us-east-1", min_length=1)
    service_name: str = Field(default="loop-cp-api", min_length=1)
    request_id_header: str = Field(default="X-Request-Id", min_length=1)
    version: str = Field(default="0.1.0", min_length=1)
    commit_sha: str = Field(default="0000000-local", min_length=7)
    build_time: str = Field(default="unknown", min_length=1)


__all__ = ["AuthProvider", "LogLevel", "Settings"]
