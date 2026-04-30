"""Salesforce server config (env-driven)."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SalesforceConfig(_StrictModel):
    """OAuth2 + instance config for the Salesforce REST API."""

    instance_url: str = Field(min_length=1)
    api_version: str = "v59.0"
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> SalesforceConfig:
        """Read config from ``SF_*`` env vars (or a supplied mapping)."""
        src = env if env is not None else dict(os.environ)
        return cls(
            instance_url=src["SF_INSTANCE_URL"],
            api_version=src.get("SF_API_VERSION", "v59.0"),
            client_id=src["SF_CLIENT_ID"],
            client_secret=src["SF_CLIENT_SECRET"],
            refresh_token=src["SF_REFRESH_TOKEN"],
        )
