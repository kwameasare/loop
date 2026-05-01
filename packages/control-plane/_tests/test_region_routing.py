"""Region-aware cp-api dispatch tests (S592)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import pytest
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.region_routing import DataPlaneResponse, RegionRouter
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceService


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any] | None = None,
    ) -> DataPlaneResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "json_body": dict(json_body) if json_body else None,
            }
        )
        return DataPlaneResponse(status_code=202, body={"accepted": True})


@pytest.mark.asyncio
async def test_cp_api_forwards_to_workspace_region_and_measures_latency() -> None:
    ticks = iter((1_000, 7_001_000))
    transport = RecordingTransport()
    svc = WorkspaceService()
    api = WorkspaceAPI(
        workspaces=svc,
        region_router=RegionRouter(clock_ns=lambda: next(ticks)),
    )
    body = await api.create(
        caller_sub="owner",
        body={"name": "Acme EU", "slug": "acme-eu", "region": "eu-west"},
    )

    result = await api.forward_data_plane_call(
        caller_sub="owner",
        workspace_id=UUID(body["id"]),
        method="post",
        path="/v1/turns",
        body={"prompt": "hello"},
        transport=transport,
        request_region="eu-west",
    )

    assert result["region"] == "eu-west"
    assert result["latency_ms"] == 7
    assert result["url"] == "https://runtime.eu-west.loop.example/v1/turns"
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"] == "https://runtime.eu-west.loop.example/v1/turns"
    assert transport.calls[0]["headers"]["X-Loop-Region"] == "eu-west"
    assert transport.calls[0]["headers"]["X-Loop-Workspace"] == body["id"]
    assert transport.calls[0]["json_body"] == {"prompt": "hello"}


@pytest.mark.asyncio
async def test_cp_api_does_not_forward_for_non_member() -> None:
    transport = RecordingTransport()
    api = WorkspaceAPI(workspaces=WorkspaceService())
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})

    with pytest.raises(AuthorisationError):
        await api.forward_data_plane_call(
            caller_sub="stranger",
            workspace_id=UUID(body["id"]),
            method="GET",
            path="/v1/turns",
            transport=transport,
        )

    assert transport.calls == []
