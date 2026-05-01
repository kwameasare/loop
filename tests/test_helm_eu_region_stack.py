"""EU data-plane stack checks for S591."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"
BASE_VALUES = CHART / "values.yaml"
EU_VALUES = CHART / "values-eu-west.yaml"
SCHEMA = CHART / "values.schema.json"
TERRAFORM_ENV = ROOT / "infra" / "terraform" / "envs" / "prod-eu-west" / "main.tf"


def _load_yaml(path: Path) -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(path.read_text(encoding="utf-8")))


def _merge(base: dict[str, object], overlay: dict[str, object]) -> dict[str, object]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(
                cast(dict[str, object], merged[key]),
                cast(dict[str, object], value),
            )
        else:
            merged[key] = value
    return merged


def test_eu_overlay_declares_full_data_plane_stack() -> None:
    overlay = _load_yaml(EU_VALUES)
    externals = cast(dict[str, str], overlay["externals"])

    for key in ("postgresUrl", "qdrantUrl", "clickhouseUrl", "natsUrl"):
        assert key in externals
        assert "eu-west" in externals[key]

    assert cast(dict[str, object], overlay["postgresql"])["enabled"] is True
    assert cast(dict[str, object], overlay["qdrant"])["enabled"] is True
    assert cast(dict[str, object], overlay["nats"])["enabled"] is True
    assert cast(dict[str, object], overlay["clickhouse"])["enabled"] is True


def test_eu_overlay_preserves_base_values_schema_parity() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    base = _load_yaml(BASE_VALUES)
    overlay = _load_yaml(EU_VALUES)
    merged = _merge(base, overlay)

    jsonschema.validate(merged, schema)
    base_externals = set(cast(dict[str, object], base["externals"]))
    eu_externals = set(cast(dict[str, object], merged["externals"]))
    assert base_externals <= eu_externals


def test_schema_rejects_missing_clickhouse_url() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    bad = _load_yaml(BASE_VALUES)
    del cast(dict[str, object], bad["externals"])["clickhouseUrl"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_terraform_env_installs_eu_helm_overlay() -> None:
    text = TERRAFORM_ENV.read_text(encoding="utf-8")

    assert 'source  = "hashicorp/helm"' in text
    assert 'source  = "hashicorp/kubernetes"' in text
    assert "values-eu-west.yaml" in text
    assert 'default     = "eu-west"' in text
    assert "region                    = var.region" in text
    assert 'residency                 = "eu"' in text
