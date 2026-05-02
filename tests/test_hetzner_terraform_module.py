"""Static checks for the Hetzner Terraform module (S775)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "infra" / "terraform" / "modules" / "hetzner-loop-stack"
ENV = ROOT / "infra" / "terraform" / "envs" / "prod-hetzner-eu-central" / "main.tf"
REGIONS = ROOT / "infra" / "terraform" / "regions.yaml"

REQUIRED_TOKENS = (
    'source  = "hetznercloud/hcloud"',
    'resource "hcloud_network" "loop"',
    'resource "hcloud_server" "control_plane"',
    'resource "hcloud_server" "worker"',
    'resource "hcloud_managed_database" "postgres"',
    'resource "helm_release" "minio"',
    'resource "helm_release" "vault"',
)


def _module_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(MODULE.glob("*.tf")))


def _module_policy_errors(text: str) -> list[str]:
    errors: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            errors.append(f"module missing {token}")
    if 'repository = "https://charts.bitnami.com/bitnami"' not in text:
        errors.append("module must install MinIO from the pinned Bitnami chart repo")
    if 'repository = "https://helm.releases.hashicorp.com"' not in text:
        errors.append("module must install Vault from the pinned HashiCorp chart repo")
    if 'engine   = "postgresql"' not in text:
        errors.append("module must provision managed Postgres")
    return errors


def test_hetzner_module_covers_cost_optimized_services() -> None:
    assert _module_policy_errors(_module_text()) == []


def test_hetzner_env_resolves_region_from_registry() -> None:
    text = ENV.read_text(encoding="utf-8")

    assert 'source  = "hetznercloud/hcloud"' in text
    assert 'default     = "eu-cost"' in text
    assert "local.region.concrete.hetzner" in text
    assert 'source          = "../../modules/hetzner-loop-stack"' in text


def test_regions_registry_contains_hetzner_cost_region() -> None:
    data = cast(dict[str, Any], yaml.safe_load(REGIONS.read_text(encoding="utf-8")))
    regions = cast(dict[str, Any], data["regions"])
    cost = cast(dict[str, Any], regions["eu-cost"])
    concrete = cast(dict[str, str], cost["concrete"])

    assert cost["residency"] == "EU"
    assert concrete["hetzner"] == "fsn1"


def test_hetzner_policy_rejects_missing_minio_and_vault() -> None:
    bad = _module_text().replace('resource "helm_release" "minio"', "")
    bad = bad.replace('resource "helm_release" "vault"', "")

    assert _module_policy_errors(bad) == [
        'module missing resource "helm_release" "minio"',
        'module missing resource "helm_release" "vault"',
    ]
