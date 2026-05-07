"""Region registry helpers for workspace data residency."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

DEFAULT_REGIONS_PATH = (
    Path(__file__).resolve().parents[3] / "infra" / "terraform" / "regions.yaml"
)
PACKAGED_REGIONS_PATH = Path(__file__).with_name("regions.yaml")
_FALLBACK_REGIONS_YAML = """
default_region: na-east
regions:
  na-east:
    display_name: North America East
    residency: US
    primary: true
    data_plane_url: https://runtime.na-east.loop.example
    concrete:
      aws: us-east-1
      azure: eastus
      gcp: us-east1
  eu-west:
    display_name: Europe West
    residency: EU
    primary: false
    data_plane_url: https://runtime.eu-west.loop.example
    concrete:
      aws: eu-central-1
      azure: westeurope
      gcp: europe-west1
  cn-shanghai:
    display_name: China Shanghai
    residency: CN
    primary: false
    data_plane_url: https://runtime.cn-shanghai.loop.example
    concrete:
      alibaba: cn-shanghai
  eu-sovereign:
    display_name: Europe Sovereign
    residency: EU
    primary: false
    data_plane_url: https://runtime.eu-sovereign.loop.example
    concrete:
      ovh: GRA11
  eu-cost:
    display_name: Europe Cost Optimized
    residency: EU
    primary: false
    data_plane_url: https://runtime.eu-cost.loop.example
    concrete:
      hetzner: fsn1
"""


class RegionError(ValueError):
    """Raised when a workspace references an unknown or invalid region."""


@dataclass(frozen=True)
class Region:
    slug: str
    display_name: str
    residency: str
    data_plane_url: str
    concrete: dict[str, str]
    primary: bool = False


@dataclass(frozen=True)
class RegionRegistry:
    default_region: str
    regions: dict[str, Region]

    def require(self, slug: str) -> Region:
        try:
            return self.regions[slug]
        except KeyError as exc:
            known = ", ".join(sorted(self.regions))
            raise RegionError(f"unknown region '{slug}'; expected one of: {known}") from exc

    def require_same(self, *, workspace_region: str, request_region: str) -> None:
        self.require(workspace_region)
        self.require(request_region)
        if request_region != workspace_region:
            raise RegionError(
                "cross-region workspace access denied: "
                f"workspace is pinned to '{workspace_region}', request used '{request_region}'"
            )


def _require_mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegionError(f"{name} must be a mapping")
    return cast(dict[str, Any], value)


def _require_str(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise RegionError(f"{name} must be a non-empty string")
    return value


def _read_default_regions_yaml() -> str:
    configured_path = os.environ.get("LOOP_REGIONS_PATH")
    if configured_path:
        return Path(configured_path).expanduser().read_text(encoding="utf-8")
    if DEFAULT_REGIONS_PATH.exists():
        return DEFAULT_REGIONS_PATH.read_text(encoding="utf-8")
    if PACKAGED_REGIONS_PATH.exists():
        return PACKAGED_REGIONS_PATH.read_text(encoding="utf-8")
    return _FALLBACK_REGIONS_YAML


def load_region_registry(path: Path | None = None) -> RegionRegistry:
    raw_text = (
        path.read_text(encoding="utf-8")
        if path is not None
        else _read_default_regions_yaml()
    )
    raw = yaml.safe_load(raw_text)
    data = _require_mapping(raw, name="regions.yaml")
    default_region = _require_str(data.get("default_region"), name="default_region")
    raw_regions = _require_mapping(data.get("regions"), name="regions")
    regions: dict[str, Region] = {}
    for slug, value in raw_regions.items():
        region_data = _require_mapping(value, name=f"regions.{slug}")
        concrete = _require_mapping(region_data.get("concrete"), name=f"{slug}.concrete")
        region_slug = _require_str(slug, name="region slug")
        regions[region_slug] = Region(
            slug=region_slug,
            display_name=_require_str(region_data.get("display_name"), name=f"{slug}.display_name"),
            residency=_require_str(region_data.get("residency"), name=f"{slug}.residency"),
            data_plane_url=_require_str(
                region_data.get("data_plane_url"), name=f"{slug}.data_plane_url"
            ),
            primary=bool(region_data.get("primary", False)),
            concrete={
                str(cloud): _require_str(region, name=f"{slug}.{cloud}")
                for cloud, region in concrete.items()
            },
        )
    registry = RegionRegistry(default_region=default_region, regions=regions)
    registry.require(default_region)
    return registry


@cache
def default_region_registry() -> RegionRegistry:
    return load_region_registry()
