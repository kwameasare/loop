"""Structural test for the AWS Loop terraform module (S904).

Terraform isn't generally installed in the CI environment, so this test
asserts on the *file shape* of the module: every resource the AC calls
out (KMS, S3, EKS, RDS, ElastiCache, CloudFront), every variable the
companion env needs, every output the helm chart consumes.

A live ``terraform validate`` run is gated on
``LOOP_TERRAFORM_VALIDATE=1`` and only fires when the ``terraform`` CLI
is on ``$PATH``. See bottom of this file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = ROOT / "infra" / "terraform" / "modules" / "aws-loop-stack"
ENV_DIR = ROOT / "infra" / "terraform" / "envs" / "staging-aws-us-east-2"


# --------------------------------------------------------------------------- #
# Module files exist                                                          #
# --------------------------------------------------------------------------- #


def test_module_directory_exists() -> None:
    assert MODULE_DIR.is_dir(), f"module directory missing: {MODULE_DIR}"


@pytest.mark.parametrize("filename", ["main.tf", "variables.tf", "outputs.tf"])
def test_module_has_required_file(filename: str) -> None:
    path = MODULE_DIR / filename
    assert path.is_file(), f"module file missing: {path}"
    assert path.stat().st_size > 0, f"module file empty: {path}"


# --------------------------------------------------------------------------- #
# Module covers every AWS resource the AC requires                            #
# --------------------------------------------------------------------------- #


def _main_tf() -> str:
    return (MODULE_DIR / "main.tf").read_text()


@pytest.mark.parametrize(
    "resource_type",
    [
        "aws_kms_key",
        "aws_kms_alias",
        "aws_s3_bucket",
        "aws_s3_bucket_server_side_encryption_configuration",
        "aws_s3_bucket_versioning",
        "aws_s3_bucket_public_access_block",
        "aws_eks_cluster",
        "aws_eks_node_group",
        "aws_iam_role",
        "aws_db_instance",
        "aws_db_subnet_group",
        "aws_elasticache_replication_group",
        "aws_elasticache_subnet_group",
        "aws_cloudfront_distribution",
    ],
)
def test_main_tf_declares_resource(resource_type: str) -> None:
    assert f'resource "{resource_type}"' in _main_tf(), (
        f"module main.tf missing resource type {resource_type!r}"
    )


def test_kms_key_has_rotation_enabled() -> None:
    """Every Loop KMS key must enable annual rotation per SECURITY.md §5."""
    body = _main_tf()
    assert "enable_key_rotation     = true" in body or "enable_key_rotation = true" in body, (
        "KMS key must have enable_key_rotation=true"
    )


def test_s3_bucket_uses_kms_encryption() -> None:
    body = _main_tf()
    assert 'sse_algorithm     = "aws:kms"' in body or 'sse_algorithm = "aws:kms"' in body, (
        "S3 bucket SSE must be aws:kms (no SSE-S3 / unencrypted buckets)"
    )


def test_s3_bucket_blocks_public_access() -> None:
    body = _main_tf()
    assert "block_public_acls       = true" in body or "block_public_acls = true" in body
    assert "restrict_public_buckets = true" in body or "restrict_public_buckets = true" in body


def test_rds_postgres_uses_kms_encryption() -> None:
    body = _main_tf()
    assert "storage_encrypted      = true" in body or "storage_encrypted = true" in body, (
        "RDS storage_encrypted must be true"
    )


def test_rds_postgres_has_deletion_protection() -> None:
    body = _main_tf()
    assert "deletion_protection    = true" in body or "deletion_protection = true" in body


def test_rds_postgres_is_multi_az() -> None:
    body = _main_tf()
    assert "multi_az               = true" in body or "multi_az = true" in body


def test_redis_has_at_rest_and_transit_encryption() -> None:
    body = _main_tf()
    assert "at_rest_encryption_enabled = true" in body, "ElastiCache Redis must encrypt at rest"
    assert "transit_encryption_enabled = true" in body, "ElastiCache Redis must encrypt in transit"


def test_eks_endpoint_is_private() -> None:
    """EKS control plane must not be publicly reachable; use VPN/PrivateLink."""
    body = _main_tf()
    assert "endpoint_public_access  = false" in body or "endpoint_public_access = false" in body


def test_eks_secrets_envelope_encryption() -> None:
    """EKS secrets must be envelope-encrypted with the Loop KMS key."""
    body = _main_tf()
    assert 'resources = ["secrets"]' in body
    assert "key_arn = aws_kms_key.loop.arn" in body


# --------------------------------------------------------------------------- #
# Variables every env file needs                                              #
# --------------------------------------------------------------------------- #


def _variables_tf() -> str:
    return (MODULE_DIR / "variables.tf").read_text()


@pytest.mark.parametrize(
    "name",
    [
        "name_prefix",
        "loop_region",
        "aws_region",
        "vpc_id",
        "subnet_ids",
        "postgres_allowed_cidrs",
        "redis_allowed_cidrs",
        "s3_bucket_name",
        "postgres_master_password",
        "worker_instance_types",
    ],
)
def test_module_declares_variable(name: str) -> None:
    assert f'variable "{name}"' in _variables_tf(), f"module variables.tf missing variable {name!r}"


def test_postgres_master_password_marked_sensitive() -> None:
    body = _variables_tf()
    # Take the postgres_master_password block and assert it has sensitive=true.
    block_start = body.index('variable "postgres_master_password"')
    block = body[block_start : block_start + 400]
    assert "sensitive   = true" in block or "sensitive = true" in block


def test_subnet_ids_validation_requires_two() -> None:
    body = _variables_tf()
    assert "length(var.subnet_ids) >= 2" in body


# --------------------------------------------------------------------------- #
# Outputs the helm chart / runtime depends on                                 #
# --------------------------------------------------------------------------- #


def _outputs_tf() -> str:
    return (MODULE_DIR / "outputs.tf").read_text()


@pytest.mark.parametrize(
    "name",
    [
        "eks_cluster_id",
        "eks_cluster_endpoint",
        "postgres_endpoint",
        "redis_primary_endpoint",
        "s3_bucket",
        "kms_key_id",
        "kms_key_arn",
    ],
)
def test_module_declares_output(name: str) -> None:
    assert f'output "{name}"' in _outputs_tf(), f"module outputs.tf missing output {name!r}"


# --------------------------------------------------------------------------- #
# Staging env wiring                                                          #
# --------------------------------------------------------------------------- #


def test_staging_env_exists() -> None:
    assert ENV_DIR.is_dir(), f"staging env dir missing: {ENV_DIR}"
    assert (ENV_DIR / "main.tf").is_file()


def test_staging_env_pins_loop_region() -> None:
    body = (ENV_DIR / "main.tf").read_text()
    # Must constrain to na-east per the cloud-portability convention.
    assert 'default     = "na-east"' in body or 'default = "na-east"' in body
    assert 'var.loop_region == "na-east"' in body


def test_staging_env_uses_module() -> None:
    body = (ENV_DIR / "main.tf").read_text()
    assert 'source                   = "../../modules/aws-loop-stack"' in body or (
        'source = "../../modules/aws-loop-stack"' in body
    )


def test_staging_env_resolves_aws_region_from_yaml() -> None:
    body = (ENV_DIR / "main.tf").read_text()
    assert "yamldecode(file" in body
    assert "regions.yaml" in body
    assert "local.region.concrete.aws" in body


@pytest.mark.parametrize(
    "name",
    [
        "vpc_id",
        "subnet_ids",
        "postgres_allowed_cidrs",
        "redis_allowed_cidrs",
        "s3_bucket_name",
        "postgres_master_password",
    ],
)
def test_staging_env_passes_required_var(name: str) -> None:
    body = (ENV_DIR / "main.tf").read_text()
    assert f"{name}" in body, f"staging env missing var {name!r}"


# --------------------------------------------------------------------------- #
# Live `terraform validate` (only when terraform is installed)                #
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    shutil.which("terraform") is None or os.environ.get("LOOP_TERRAFORM_VALIDATE") != "1",
    reason="terraform not on PATH or LOOP_TERRAFORM_VALIDATE!=1",
)
def test_module_passes_terraform_validate() -> None:
    """If terraform is installed, run `terraform init -backend=false` and
    `terraform validate` against the module to catch syntax errors."""
    init = subprocess.run(
        ["terraform", "init", "-backend=false", "-input=false", "-no-color"],
        cwd=MODULE_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert init.returncode == 0, (
        f"terraform init failed:\nstdout={init.stdout}\nstderr={init.stderr}"
    )
    validate = subprocess.run(
        ["terraform", "validate", "-no-color"],
        cwd=MODULE_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert validate.returncode == 0, (
        f"terraform validate failed:\nstdout={validate.stdout}\nstderr={validate.stderr}"
    )
