"""Tests for bundled Qdrant subchart dependency added in S448."""

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


def test_chart_declares_qdrant_dependency_pinned_with_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    qd = next((d for d in deps if d.get("name") == "qdrant"), None)
    assert qd is not None, "qdrant dependency must be declared"
    version = cast(str, qd["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    repo = cast(str, qd["repository"])
    assert "qdrant" in repo, "must use Qdrant's official chart per S448 AC"
    assert qd.get("condition") == "qdrant.enabled"


def test_values_qdrant_block_aligns_with_externals_url() -> None:
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    qd = cast(dict[str, object], values["qdrant"])
    assert qd["enabled"] is True
    assert qd.get("fullnameOverride") == "loop-qdrant"
    externals = cast(dict[str, object], values["externals"])
    assert "loop-qdrant" in cast(str, externals["qdrantUrl"])
