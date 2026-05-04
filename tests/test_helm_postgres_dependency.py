"""Tests for bundled Postgres subchart dependency added in S446."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
CHART_YAML = CHART / "Chart.yaml"
VALUES = CHART / "values.yaml"
SCHEMA = CHART / "values.schema.json"


def _chart() -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(CHART_YAML.read_text()))


def test_chart_declares_postgresql_dependency_pinned() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    pg = next((d for d in deps if d.get("name") == "postgresql"), None)
    assert pg is not None, "postgresql dependency must be declared"
    version = cast(str, pg["version"])
    assert re.match(r"^\d+\.\d+\.\d+$", version), f"pinned exact semver expected, got {version!r}"
    repo = cast(str, pg["repository"])
    assert repo.startswith("oci://"), "mirror repository must be OCI-backed"
    assert "ghcr.io/loop-ai/mirrored/bitnami/charts" in repo


def test_chart_postgres_dependency_has_condition() -> None:
    deps = cast(list[dict[str, object]], _chart().get("dependencies", []))
    pg = next((d for d in deps if d.get("name") == "postgresql"), None)
    assert pg is not None
    assert pg.get("condition") == "postgresql.enabled", (
        "condition must allow bypass via postgresql.enabled=false"
    )


def test_values_postgresql_block_defaults_present() -> None:
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    pg = cast(dict[str, object], values["postgresql"])
    assert pg["enabled"] is True
    auth = cast(dict[str, object], pg["auth"])
    assert auth["database"] == "loop"
    assert auth["username"] == "loop"


def test_externals_postgresurl_aligns_with_subchart_fullname() -> None:
    """When bundled, externals.postgresUrl must resolve to the subchart's
    Service. We pin fullnameOverride=loop-postgres so the URL is stable
    regardless of release name."""
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    pg = cast(dict[str, object], values["postgresql"])
    primary = cast(dict[str, object], pg.get("primary", {}))
    assert pg.get("fullnameOverride") == "loop-postgres"
    externals = cast(dict[str, object], values["externals"])
    assert "loop-postgres" in cast(str, externals["postgresUrl"])
    # ensure persistence is wired so the bundled DB is durable by default
    persistence = cast(dict[str, object], primary.get("persistence", {}))
    assert persistence.get("enabled") is True


def test_schema_allows_postgresql_block() -> None:
    """Schema permits unknown top-level keys for overlays; this test
    confirms postgresql remains acceptable to the schema."""
    schema = json.loads(SCHEMA.read_text())
    values = cast(dict[str, object], yaml.safe_load(VALUES.read_text()))
    jsonschema.validate(values, schema)
