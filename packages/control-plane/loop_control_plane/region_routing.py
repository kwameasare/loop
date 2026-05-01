"""Region-aware forwarding helpers for cp-api data-plane calls."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from loop_control_plane.regions import RegionRegistry, default_region_registry
from loop_control_plane.workspaces import Workspace


@dataclass(frozen=True)
class DataPlaneResponse:
    status_code: int
    body: Mapping[str, Any] | None = None
    headers: Mapping[str, str] | None = None


@dataclass(frozen=True)
class RegionDispatchResult:
    status_code: int
    body: Mapping[str, Any] | None
    headers: dict[str, str]
    region: str
    url: str
    latency_ms: int


class DataPlaneTransport(Protocol):
    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any] | None = None,
    ) -> DataPlaneResponse: ...


class RegionRouter:
    def __init__(
        self,
        *,
        regions: RegionRegistry | None = None,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
    ) -> None:
        self._regions = regions or default_region_registry()
        self._clock_ns = clock_ns

    async def forward(
        self,
        *,
        workspace: Workspace,
        method: str,
        path: str,
        transport: DataPlaneTransport,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> RegionDispatchResult:
        region = self._regions.require(workspace.region)
        url = f"{region.data_plane_url.rstrip('/')}/{path.lstrip('/')}"
        outbound_headers = {
            **(dict(headers) if headers else {}),
            "X-Loop-Region": region.slug,
            "X-Loop-Workspace": str(workspace.id),
        }
        started = self._clock_ns()
        response = await transport.request(
            method=method.upper(),
            url=url,
            headers=outbound_headers,
            json_body=json_body,
        )
        latency_ms = max(0, (self._clock_ns() - started) // 1_000_000)
        return RegionDispatchResult(
            status_code=response.status_code,
            body=response.body,
            headers=dict(response.headers or {}),
            region=region.slug,
            url=url,
            latency_ms=latency_ms,
        )
