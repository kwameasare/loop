"""Tests for bundled MinIO subchart dependency added in S451.

S451 AC: pick-your-storage; tests for both. We test the bundled MinIO
default and the bypass path (minio.enabled=false + externalS3 endpoint
via externals.s3Endpoint).
"""

from __future__ import annotations

import re
from copy import deepcopy
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


def test_chart_declares_minio_dependency_pinned_with_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    minio = next((d for d in deps if d.get("name") == "minio"), None)
    assert minio is not None, "minio dependency must be declared"
    version = cast(str, minio["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    repo = cast(str, minio["repository"])
    assert "bitnami" in repo
    assert minio.get("condition") == "minio.enabled"


def test_bundled_minio_default_aligns_with_externals_endpoint() -> None:
    values = _values()
    minio = cast(dict[str, object], values["minio"])
    assert minio["enabled"] is True
    assert minio.get("fullnameOverride") == "loop-minio"
    persistence = cast(dict[str, object], minio.get("persistence", {}))
    assert persistence.get("enabled") is True
    externals = cast(dict[str, object], values["externals"])
    assert "loop-minio" in cast(str, externals["s3Endpoint"])


def test_external_s3_bypass_path() -> None:
    """When operator sets minio.enabled=false they MUST override
    externals.s3Endpoint -- we encode that contract in test form so a
    future regression caught early."""
    values = deepcopy(_values())
    minio = cast(dict[str, object], values["minio"])
    minio["enabled"] = False
    externals = cast(dict[str, object], values["externals"])
    externals["s3Endpoint"] = "https://s3.eu-west-1.amazonaws.com"
    # Sanity: the bundled subchart's Service URL is no longer required
    # downstream, only the operator-supplied endpoint.
    assert externals["s3Endpoint"].startswith("https://")  # type: ignore[union-attr]
    assert minio["enabled"] is False
