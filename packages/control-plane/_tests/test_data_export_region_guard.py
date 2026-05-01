"""Cross-region data export guard tests (S593)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import pytest
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.errors import map_to_loop_api_error
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceService


class RecordingExportStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def load_workspace_export(
        self,
        *,
        workspace_id: UUID,
        export_id: str,
        region: str,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "workspace_id": str(workspace_id),
                "export_id": export_id,
                "region": region,
            }
        )
        return {"export_id": export_id, "region": region, "status": "ready"}


@pytest.mark.asyncio
async def test_data_export_loads_from_workspace_region() -> None:
    api = WorkspaceAPI(workspaces=WorkspaceService())
    store = RecordingExportStore()
    body = await api.create(
        caller_sub="owner",
        body={"name": "Acme EU", "slug": "acme-eu", "region": "eu-west"},
    )
    ws_id = UUID(body["id"])

    result = await api.load_data_export(
        caller_sub="owner",
        workspace_id=ws_id,
        export_id="exp-1",
        export_region="eu-west",
        store=store,
        request_region="eu-west",
    )

    assert result == {"export_id": "exp-1", "region": "eu-west", "status": "ready"}
    assert store.calls == [{"workspace_id": body["id"], "export_id": "exp-1", "region": "eu-west"}]


@pytest.mark.asyncio
async def test_cross_region_data_export_is_403_before_load() -> None:
    api = WorkspaceAPI(workspaces=WorkspaceService())
    store = RecordingExportStore()
    body = await api.create(
        caller_sub="owner",
        body={"name": "Acme EU", "slug": "acme-eu", "region": "eu-west"},
    )

    with pytest.raises(AuthorisationError) as excinfo:
        await api.load_data_export(
            caller_sub="owner",
            workspace_id=UUID(body["id"]),
            export_id="exp-1",
            export_region="na-east",
            store=store,
            request_region="eu-west",
        )

    assert store.calls == []
    error = map_to_loop_api_error(excinfo.value, request_id="r-1")
    assert error.status == 403
    assert "cross-region data export" in error.message
