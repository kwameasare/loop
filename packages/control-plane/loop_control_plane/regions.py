"""Region registry helpers for workspace data residency."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

DEFAULT_REGIONS_PATH = Path(__file__).resolve().parents[3] / "infra" / "terraform" / "regions.yaml"


class RegionError(ValueError):
    """Raised when a workspace references an unknown or invalid region."""


@dataclass(frozen=True)
class Region:
    slug: str
    display_name: str
    residency: str
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


def load_region_registry(path: Path = DEFAULT_REGIONS_PATH) -> RegionRegistry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
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
