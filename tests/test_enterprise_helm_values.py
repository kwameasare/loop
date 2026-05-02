"""Smoke tests for the dedicated enterprise Helm values overlay (S638)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "infra" / "helm" / "loop"
BASE_VALUES = CHART_DIR / "values.yaml"
ENTERPRISE_VALUES = CHART_DIR / "values-enterprise.yaml"
SCHEMA_PATH = CHART_DIR / "values.schema.json"

STATEFUL_DEPS: tuple[tuple[str, str, str], ...] = (
    ("postgresql", "postgresUrl", "postgres"),
    ("redis", "redisUrl", "redis"),
    ("qdrant", "qdrantUrl", "qdrant"),
    ("nats", "natsUrl", "nats"),
    ("minio", "s3Endpoint", "minio"),
    ("clickhouse", "clickhouseUrl", "clickhouse"),
)


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        base_value = merged.get(key)
        if isinstance(value, dict) and isinstance(base_value, dict):
            merged[key] = _deep_merge(cast(dict[str, Any], base_value), cast(dict[str, Any], value))
        else:
            merged[key] = value
    return merged


def _enterprise_values() -> dict[str, Any]:
    return _deep_merge(_load_yaml(BASE_VALUES), _load_yaml(ENTERPRISE_VALUES))


def _enterprise_isolation_errors(values: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    global_values = cast(dict[str, Any], values.get("global", {}))
    externals = cast(dict[str, Any], values.get("externals", {}))
    prefix = str(values.get("fullnameOverride", ""))
    if global_values.get("deploymentMode") != "enterprise":
        errors.append("enterprise overlay must set global.deploymentMode=enterprise")
    if not global_values.get("customerId"):
        errors.append("enterprise overlay must set a customer id")
    isolation = cast(dict[str, Any], global_values.get("isolation", {}))
    if isolation.get("dedicatedStack") is not True:
        errors.append("enterprise overlay must request a dedicated stack")
    if not prefix.startswith("loop-enterprise-"):
        errors.append("enterprise overlay must use a customer-scoped fullnameOverride")
    for section, external_key, suffix in STATEFUL_DEPS:
        dep = cast(dict[str, Any], values.get(section, {}))
        expected = f"{prefix}-{suffix}"
        if dep.get("enabled") is not True:
            errors.append(f"{section} must stay enabled for an isolated bundled stack")
        if dep.get("fullnameOverride") != expected:
            errors.append(f"{section} must use customer-scoped fullnameOverride {expected}")
        if expected not in str(externals.get(external_key, "")):
            errors.append(f"externals.{external_key} must point at {expected}")
    return errors


def test_enterprise_values_validate_against_chart_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.validate(_enterprise_values(), schema)


def test_enterprise_values_produce_customer_isolated_stack() -> None:
    values = _enterprise_values()

    assert _enterprise_isolation_errors(values) == []
    for section in ("controlPlane", "runtime", "gateway", "kbEngine", "toolHost"):
        component = cast(dict[str, Any], values[section])
        assert component["replicaCount"] >= 2


def test_enterprise_isolation_policy_rejects_shared_redis() -> None:
    values = _enterprise_values()
    redis = cast(dict[str, Any], values["redis"])
    externals = cast(dict[str, Any], values["externals"])
    redis["fullnameOverride"] = "loop-redis"
    externals["redisUrl"] = "redis://loop-redis:6379/0"

    assert _enterprise_isolation_errors(values) == [
        "redis must use customer-scoped fullnameOverride loop-enterprise-acme-redis",
        "externals.redisUrl must point at loop-enterprise-acme-redis",
    ]
