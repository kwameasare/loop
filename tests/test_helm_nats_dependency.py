"""Tests for bundled NATS subchart dependency added in S449."""

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


def test_chart_declares_nats_dependency_pinned_with_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    nats = next((d for d in deps if d.get("name") == "nats"), None)
    assert nats is not None, "nats dependency must be declared"
    version = cast(str, nats["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    repo = cast(str, nats["repository"])
    assert "nats-io" in repo
    assert nats.get("condition") == "nats.enabled"


def test_values_nats_block_has_jetstream_enabled() -> None:
    """S449 AC: jetstream-on. We persist JetStream so durable
    consumers survive restarts."""
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    nats = cast(dict[str, object], values["nats"])
    assert nats["enabled"] is True
    assert nats.get("fullnameOverride") == "loop-nats"
    config = cast(dict[str, object], nats["config"])
    js = cast(dict[str, object], config["jetstream"])
    assert js["enabled"] is True
    fs = cast(dict[str, object], js["fileStore"])
    assert fs["enabled"] is True
    externals = cast(dict[str, object], values["externals"])
    assert "loop-nats" in cast(str, externals["natsUrl"])
