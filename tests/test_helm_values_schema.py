"""Validate infra/helm/loop/values.schema.json against the base values.yaml.

helm itself runs this schema on every `helm install` / `helm upgrade`
(see https://helm.sh/docs/topics/charts/#schema-files); we replicate the
check in CI so a broken schema or values file fails fast without needing
the helm binary.

Story: S440 (helm umbrella chart skeleton + values.schema.json) [extends S036]
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "infra" / "helm" / "loop"
SCHEMA_PATH = CHART_DIR / "values.schema.json"
BASE_VALUES = CHART_DIR / "values.yaml"


def _load_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file(), f"missing {SCHEMA_PATH}"


def test_schema_is_self_valid_draft_2020_12() -> None:
    schema = _load_schema()
    declared = schema.get("$schema", "")
    assert isinstance(declared, str) and declared.endswith("/2020-12/schema")
    jsonschema.Draft202012Validator.check_schema(schema)


def test_base_values_validate_against_schema() -> None:
    schema = _load_schema()
    values = _load_yaml(BASE_VALUES)
    jsonschema.validate(values, schema)


def test_schema_rejects_negative_replica_count() -> None:
    schema = _load_schema()
    bad = copy.deepcopy(_load_yaml(BASE_VALUES))
    assert isinstance(bad["controlPlane"], dict)
    bad["controlPlane"]["replicaCount"] = 0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_schema_rejects_unknown_image_pull_policy() -> None:
    schema = _load_schema()
    bad = copy.deepcopy(_load_yaml(BASE_VALUES))
    assert isinstance(bad["global"], dict)
    bad["global"]["imagePullPolicy"] = "Sometimes"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_schema_rejects_unknown_deployment_mode() -> None:
    schema = _load_schema()
    bad = copy.deepcopy(_load_yaml(BASE_VALUES))
    assert isinstance(bad["global"], dict)
    bad["global"]["deploymentMode"] = "partial"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_schema_rejects_missing_required_top_level_section() -> None:
    schema = _load_schema()
    bad = copy.deepcopy(_load_yaml(BASE_VALUES))
    del bad["secrets"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_schema_allows_regional_overlay_extra_keys() -> None:
    """Overlays add governance sections (audit, networkPolicy, telemetry).

    The base schema must not block top-level extension keys so cross-region
    overlays compose with `helm install -f values-region.yaml` cleanly.
    """
    schema = _load_schema()
    extended = copy.deepcopy(_load_yaml(BASE_VALUES))
    extended["audit"] = {"enabled": True, "hotRetentionDays": 365}
    extended["networkPolicy"] = {"enforceRegionPin": True}
    extended["telemetry"] = {"metricsEndpoint": "https://metrics.example/"}
    jsonschema.validate(extended, schema)
