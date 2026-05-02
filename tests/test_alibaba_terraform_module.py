"""Static checks for the Alibaba Cloud Terraform module (S773)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "infra" / "terraform" / "modules" / "alibaba-loop-stack"
ENV = ROOT / "infra" / "terraform" / "envs" / "prod-alibaba-cn-shanghai" / "main.tf"
REGIONS = ROOT / "infra" / "terraform" / "regions.yaml"

REQUIRED_RESOURCES = (
    'resource "alicloud_cs_managed_kubernetes" "ack"',
    'resource "alicloud_db_instance" "postgres"',
    'resource "alicloud_kvstore_instance" "redis"',
    'resource "alicloud_oss_bucket" "objects"',
    'resource "alicloud_kms_key" "loop"',
    'resource "alicloud_dcdn_domain" "edge"',
)


def _module_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(MODULE.glob("*.tf")))


def _module_policy_errors(text: str) -> list[str]:
    errors: list[str] = []
    if 'source  = "aliyun/alicloud"' not in text:
        errors.append("module must use the Alibaba Cloud provider")
    for resource in REQUIRED_RESOURCES:
        if resource not in text:
            errors.append(f"module missing {resource}")
    if "alicloud_oss_bucket_server_side_encryption_rule" not in text:
        errors.append("OSS bucket must be KMS-encrypted")
    if "slb_internet_enabled  = false" not in text:
        errors.append("ACK API load balancer must stay private by default")
    if "deletion_protection   = true" not in text:
        errors.append("ACK cluster must enable deletion protection")
    return errors


def test_alibaba_module_covers_required_cloud_services() -> None:
    assert _module_policy_errors(_module_text()) == []


def test_alibaba_env_resolves_concrete_region_from_regions_yaml() -> None:
    text = ENV.read_text(encoding="utf-8")

    assert 'source  = "aliyun/alicloud"' in text
    assert 'default     = "cn-shanghai"' in text
    assert "yamldecode(file(\"${path.module}/../../regions.yaml\"))" in text
    assert "local.region.concrete.alibaba" in text
    assert 'source                 = "../../modules/alibaba-loop-stack"' in text


def test_regions_registry_contains_alibaba_china_region() -> None:
    data = cast(dict[str, Any], yaml.safe_load(REGIONS.read_text(encoding="utf-8")))
    regions = cast(dict[str, Any], data["regions"])
    china = cast(dict[str, Any], regions["cn-shanghai"])
    concrete = cast(dict[str, str], china["concrete"])

    assert china["residency"] == "CN"
    assert concrete["alibaba"] == "cn-shanghai"


def test_module_policy_rejects_missing_kms_and_edge() -> None:
    text = _module_text()
    bad_text = text.replace('resource "alicloud_kms_key" "loop"', "")
    bad_text = bad_text.replace('resource "alicloud_dcdn_domain" "edge"', "")

    assert _module_policy_errors(bad_text) == [
        'module missing resource "alicloud_kms_key" "loop"',
        'module missing resource "alicloud_dcdn_domain" "edge"',
    ]
