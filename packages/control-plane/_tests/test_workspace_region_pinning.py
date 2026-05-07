"""Workspace region pinning tests (S590)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import loop_control_plane.regions as regions_module
import pytest
import yaml
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.errors import map_to_loop_api_error
from loop_control_plane.regions import DEFAULT_REGIONS_PATH, load_region_registry
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import WorkspaceError, WorkspaceService


@pytest.fixture
def api() -> WorkspaceAPI:
    return WorkspaceAPI(workspaces=WorkspaceService())


def test_region_registry_loads_abstract_regions() -> None:
    registry = load_region_registry(DEFAULT_REGIONS_PATH)

    assert registry.default_region == "na-east"
    assert registry.require("na-east").concrete["aws"] == "us-east-1"
    assert registry.require("eu-west").residency == "EU"


def test_region_registry_uses_runtime_fallback_when_repo_file_is_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LOOP_REGIONS_PATH", raising=False)
    monkeypatch.setattr(
        regions_module, "DEFAULT_REGIONS_PATH", tmp_path / "missing.yaml"
    )
    monkeypatch.setattr(
        regions_module, "PACKAGED_REGIONS_PATH", tmp_path / "also-missing.yaml"
    )

    registry = regions_module.load_region_registry()

    assert registry.default_region == "na-east"
    assert registry.require("eu-cost").concrete["hetzner"] == "fsn1"


def test_region_registry_honors_configured_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "regions.yaml"
    path.write_text(
        """
default_region: lab
regions:
  lab:
    display_name: Lab
    residency: test
    data_plane_url: https://runtime.lab.loop.example
    concrete:
      aws: us-test-1
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOOP_REGIONS_PATH", str(path))

    registry = regions_module.load_region_registry()

    assert registry.default_region == "lab"
    assert registry.require("lab").concrete["aws"] == "us-test-1"


def test_openapi_documents_workspace_region_contract() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    spec_path = repo_root / "loop_implementation" / "api" / "openapi.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    schemas = spec["components"]["schemas"]
    assert schemas["WorkspaceCreate"]["properties"]["region"]["default"] == "na-east"
    assert "region" not in schemas["WorkspacePatch"]["properties"]
    assert spec["components"]["parameters"]["RequestRegion"]["name"] == "X-Loop-Region"


@pytest.mark.asyncio
async def test_create_accepts_region_pin(api: WorkspaceAPI) -> None:
    body = await api.create(
        caller_sub="u-1",
        body={"name": "Acme EU", "slug": "acme-eu", "region": "eu-west"},
    )

    assert body["region"] == "eu-west"


@pytest.mark.asyncio
async def test_create_rejects_unknown_region(api: WorkspaceAPI) -> None:
    with pytest.raises(WorkspaceError):
        await api.create(
            caller_sub="u-1",
            body={"name": "Acme", "slug": "acme", "region": "antarctica-1"},
        )


@pytest.mark.asyncio
async def test_patch_rejects_region_change(api: WorkspaceAPI) -> None:
    body = await api.create(caller_sub="owner", body={"name": "Acme", "slug": "acme"})
    ws_id = UUID(body["id"])

    with pytest.raises(WorkspaceError, match="immutable"):
        await api.patch(
            caller_sub="owner",
            workspace_id=ws_id,
            body={"region": "eu-west"},
        )

    fetched = await api.get(caller_sub="owner", workspace_id=ws_id)
    assert fetched["region"] == "na-east"


@pytest.mark.asyncio
async def test_cross_region_workspace_get_rejects_403(api: WorkspaceAPI) -> None:
    body = await api.create(
        caller_sub="owner",
        body={"name": "Acme EU", "slug": "acme-eu", "region": "eu-west"},
    )
    ws_id = UUID(body["id"])

    fetched = await api.get(caller_sub="owner", workspace_id=ws_id, request_region="eu-west")
    assert fetched["region"] == "eu-west"
    with pytest.raises(AuthorisationError, match="cross-region") as excinfo:
        await api.get(caller_sub="owner", workspace_id=ws_id, request_region="na-east")
    assert map_to_loop_api_error(excinfo.value, request_id="r-1").status == 403
