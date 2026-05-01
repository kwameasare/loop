"""Tests for bundled Redis subchart dependency added in S447."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
CHART_YAML = CHART / "Chart.yaml"
VALUES = CHART / "values.yaml"


def _chart() -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(CHART_YAML.read_text()))


def test_chart_declares_redis_dependency_pinned_with_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    redis = next((d for d in deps if d.get("name") == "redis"), None)
    assert redis is not None, "redis dependency must be declared"
    version = cast(str, redis["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    repo = cast(str, redis["repository"])
    assert "bitnami" in repo
    assert redis.get("condition") == "redis.enabled"


def test_values_redis_block_aligns_with_externals_url() -> None:
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    redis = cast(dict[str, object], values["redis"])
    assert redis["enabled"] is True
    assert redis.get("fullnameOverride") == "loop-redis"
    externals = cast(dict[str, object], values["externals"])
    assert "loop-redis" in cast(str, externals["redisUrl"])
    master = cast(dict[str, object], redis.get("master", {}))
    persistence = cast(dict[str, object], master.get("persistence", {}))
    assert persistence.get("enabled") is True
