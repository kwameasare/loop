"""Static checks for the OVHcloud Terraform module (S774)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "infra" / "terraform" / "modules" / "ovh-loop-stack"
ENV = ROOT / "infra" / "terraform" / "envs" / "prod-ovh-eu-sovereign" / "main.tf"
REGIONS = ROOT / "infra" / "terraform" / "regions.yaml"

REQUIRED_TOKENS = (
    'source  = "ovh/ovh"',
    'resource "ovh_cloud_project_kube" "cluster"',
    'resource "ovh_cloud_project_kube_nodepool" "default"',
    'resource "ovh_cloud_project_database" "postgres"',
    'resource "ovh_cloud_project_database" "redis"',
    'resource "ovh_cloud_project_region_storage" "objects"',
    'resource "helm_release" "vault"',
)


def _module_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(MODULE.glob("*.tf")))


def _module_policy_errors(text: str) -> list[str]:
    errors: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            errors.append(f"module missing {token}")
    if 'repository = "https://helm.releases.hashicorp.com"' not in text:
        errors.append("module must install Vault from the pinned HashiCorp chart repo")
    if "ha = { enabled = true, replicas = 3 }" not in text:
        errors.append("Vault Transit KMS must run in HA mode")
    if 'engine       = "postgresql"' not in text or 'engine       = "redis"' not in text:
        errors.append("module must provision managed Postgres and Redis")
    return errors


def test_ovh_module_covers_required_sovereign_services() -> None:
    assert _module_policy_errors(_module_text()) == []


def test_ovh_env_resolves_region_from_registry() -> None:
    text = ENV.read_text(encoding="utf-8")

    assert 'source  = "ovh/ovh"' in text
    assert 'default     = "eu-sovereign"' in text
    assert "local.region.concrete.ovh" in text
    assert 'endpoint = "ovh-eu"' in text
    assert 'source              = "../../modules/ovh-loop-stack"' in text


def test_regions_registry_contains_ovh_sovereign_region() -> None:
    data = cast(dict[str, Any], yaml.safe_load(REGIONS.read_text(encoding="utf-8")))
    regions = cast(dict[str, Any], data["regions"])
    sovereign = cast(dict[str, Any], regions["eu-sovereign"])
    concrete = cast(dict[str, str], sovereign["concrete"])

    assert sovereign["residency"] == "EU"
    assert concrete["ovh"] == "GRA11"


def test_ovh_policy_rejects_missing_vault_and_storage() -> None:
    bad = _module_text().replace('resource "helm_release" "vault"', "")
    bad = bad.replace('resource "ovh_cloud_project_region_storage" "objects"', "")

    assert _module_policy_errors(bad) == [
        'module missing resource "ovh_cloud_project_region_storage" "objects"',
        'module missing resource "helm_release" "vault"',
    ]
