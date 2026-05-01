"""Tests for bundled ClickHouse subchart dependency added in S450.

S450 AC: storage class param; backup config.
"""

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


def _values() -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(VALUES.read_text()))


def test_chart_declares_clickhouse_dependency_pinned_with_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    ch = next((d for d in deps if d.get("name") == "clickhouse"), None)
    assert ch is not None, "clickhouse dependency must be declared"
    version = cast(str, ch["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    assert "bitnami" in cast(str, ch["repository"])
    assert ch.get("condition") == "clickhouse.enabled"


def test_clickhouse_storage_class_param_exposed() -> None:
    """S450 AC: storage class parameterised."""
    values = _values()
    ch = cast(dict[str, object], values["clickhouse"])
    assert ch["enabled"] is True
    persistence = cast(dict[str, object], ch["persistence"])
    assert persistence["enabled"] is True
    # storageClass key must be present (even if empty -- means cluster default)
    assert "storageClass" in persistence
    assert ch.get("fullnameOverride") == "loop-clickhouse"


def test_clickhouse_backup_config_exposed() -> None:
    """S450 AC: backup config."""
    values = _values()
    ch = cast(dict[str, object], values["clickhouse"])
    backup = cast(dict[str, object], ch["backup"])
    # Default is disabled but the toggle, schedule, and retention are
    # all surfaced so an operator can flip via --set.
    assert "enabled" in backup
    assert backup["enabled"] is False
    schedule = cast(str, backup["schedule"])
    assert re.match(r"^[\d\* /,-]+$", schedule)  # crude cron sanity
    assert isinstance(backup["retentionDays"], int)
    assert cast(int, backup["retentionDays"]) > 0
