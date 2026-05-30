"""HTTP implementation of :class:`~loop_runtime.cp_client.CpApiFetcher`.

dp-runtime uses this at boot to resolve agent specs out of cp-api when
a turn request pins ``agent_id`` + ``version`` instead of carrying the
spec inline. The companion ``CpApiClient`` (in ``cp_client.py``) wraps
this fetcher with TTL caching so the hot turn path doesn't issue an HTTP
round-trip per request.

Wire protocol:
    GET  {cp_api_url}/v1/workspaces/{workspace_id}
    GET  {cp_api_url}/v1/agents/{agent_id}/versions/{version}
    GET  {cp_api_url}/v1/agents/{agent_id}/versions/active

Auth: a single shared bearer (``LOOP_RUNTIME_CP_INTERNAL_TOKEN``) is sent
on every call. cp-api's existing api-key middleware accepts it. Rotate
both sides before any shared deploy.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from loop_runtime.cp_client import (
    AgentVersionRecord,
    CpApiLookupError,
    WorkspaceRecord,
)

__all__ = ["HttpCpApiFetcher"]


class HttpCpApiFetcher:
    """httpx-backed :class:`CpApiFetcher` implementation.

    Wraps an :class:`httpx.AsyncClient` so callers can share the
    underlying connection pool (or substitute one in tests).
    """

    def __init__(
        self,
        *,
        cp_api_url: str,
        internal_token: str,
        timeout_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cp_api_url = cp_api_url.rstrip("/")
        self._internal_token = internal_token
        self._timeout_seconds = timeout_seconds
        # If the caller passed a client we trust them to manage its
        # lifecycle (the integration tests wire a transport mock). The
        # boot path constructs its own and owns close() on shutdown.
        self._client = client
        self._owns_client = client is None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._cp_api_url,
                timeout=self._timeout_seconds,
                headers=self._auth_headers(),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._internal_token}",
            "Accept": "application/json",
        }

    async def fetch_workspace(self, workspace_id: UUID) -> WorkspaceRecord:
        """``GET /v1/workspaces/{id}``. 404 → :class:`CpApiLookupError`."""
        response = await self.client.get(f"/v1/workspaces/{workspace_id}")
        if response.status_code == 404:
            raise CpApiLookupError(f"workspace {workspace_id} not found")
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return WorkspaceRecord(
            id=UUID(body["id"]),
            slug=body["slug"],
            region=body.get("region") or body.get("residency_region") or "local",
        )

    async def fetch_agent_version(
        self, *, agent_id: UUID, version: int
    ) -> AgentVersionRecord:
        """``GET /v1/agents/{agent_id}/versions/{version}``.

        version=0 is treated as a sentinel meaning "the currently
        promoted active version" so callers that don't pin a specific
        revision can still resolve. 404 → :class:`CpApiLookupError`.
        """
        path = (
            f"/v1/agents/{agent_id}/versions/"
            f"{'active' if version == 0 else version}"
        )
        response = await self.client.get(path)
        if response.status_code == 404:
            raise CpApiLookupError(
                f"agent {agent_id} version {version} not found"
            )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return AgentVersionRecord(
            agent_id=UUID(body["agent_id"]),
            version=int(body["version"]),
            config_json=dict(body.get("spec") or {}),
            workspace_id=UUID(body["workspace_id"]),
        )
