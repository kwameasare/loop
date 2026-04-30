"""Zendesk server config (env-driven)."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ZendeskConfig(_StrictModel):
    """Subdomain + API-token auth config for the Zendesk REST API."""

    subdomain: str = Field(min_length=1)
    email: str = Field(min_length=1)
    api_token: str = Field(min_length=1)
    api_version: str = "v2"

    @property
    def base_url(self) -> str:
        return f"https://{self.subdomain}.zendesk.com/api/{self.api_version}"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> ZendeskConfig:
        src = env if env is not None else dict(os.environ)
        return cls(
            subdomain=src["ZD_SUBDOMAIN"],
            email=src["ZD_EMAIL"],
            api_token=src["ZD_API_TOKEN"],
            api_version=src.get("ZD_API_VERSION", "v2"),
        )
