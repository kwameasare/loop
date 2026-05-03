"""Live integration tests for the AWS KMS + S3 backends (S905).

Runs against `localstack <https://localstack.cloud>`_ so we can exercise
real boto3 client wiring without needing an AWS account. Gated on
``LOOP_AWS_INTEGRATION=1`` so it doesn't fire on every CI run; the
hermetic stub-backed unit tests
(``packages/control-plane/_tests/test_aws_backends.py``) cover the
Protocol contract.

To run locally::

    docker run --rm -d --name loop-localstack-it \\
        -p 4566:4566 -e SERVICES=s3,kms localstack/localstack:3.7

    LOOP_AWS_INTEGRATION=1 \\
        LOOP_AWS_ENDPOINT_URL=http://127.0.0.1:4566 \\
        AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \\
        AWS_DEFAULT_REGION=us-east-1 \\
        uv run pytest tests/test_aws_backends_integration.py -q

    docker rm -f loop-localstack-it
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LOOP_AWS_INTEGRATION") != "1",
    reason="LOOP_AWS_INTEGRATION=1 not set; live AWS test skipped",
)


def _require_boto3() -> None:
    try:
        import boto3  # type: ignore[import-untyped] # noqa: F401
    except ImportError:
        pytest.skip("boto3 not installed")


@pytest.fixture(scope="module")
def aws_endpoint() -> str:
    return os.environ.get("LOOP_AWS_ENDPOINT_URL", "http://127.0.0.1:4566")


@pytest.fixture(scope="module")
def aws_region() -> str:
    return os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


# --------------------------------------------------------------------------- #
# KMS                                                                         #
# --------------------------------------------------------------------------- #


@pytest.fixture
def kms_backend_and_key(aws_endpoint: str, aws_region: str):  # type: ignore[no-untyped-def]
    _require_boto3()
    import boto3  # type: ignore[import-untyped]
    from loop_control_plane.aws_backends import (
        AwsKmsConfig,
        build_aws_kms_backend,
    )

    raw = boto3.client("kms", region_name=aws_region, endpoint_url=aws_endpoint)
    key = raw.create_key(
        Description=f"loop-it-{uuid.uuid4().hex[:8]}",
        KeyUsage="ENCRYPT_DECRYPT",
    )["KeyMetadata"]["KeyId"]

    config = AwsKmsConfig(region=aws_region, endpoint_url=aws_endpoint)
    backend = build_aws_kms_backend(config)
    return backend, key


def test_live_kms_round_trip(kms_backend_and_key) -> None:  # type: ignore[no-untyped-def]
    backend, key = kms_backend_and_key
    plaintext = b"loop integration test"
    ciphertext = backend.encrypt(key_ref=key, plaintext=plaintext)
    recovered = backend.decrypt(key_ref=key, ciphertext=ciphertext)
    assert recovered == plaintext


def test_live_kms_generate_data_key(kms_backend_and_key) -> None:  # type: ignore[no-untyped-def]
    backend, key = kms_backend_and_key
    plaintext, ciphertext = backend.generate_data_key(key_ref=key)
    assert len(plaintext) == 32  # AES-256
    recovered = backend.decrypt(key_ref=key, ciphertext=ciphertext)
    assert recovered == plaintext


def test_live_kms_describe_returns_int(kms_backend_and_key) -> None:  # type: ignore[no-untyped-def]
    backend, key = kms_backend_and_key
    rev = backend.rotate(key_ref=key)
    assert isinstance(rev, int)
    assert rev > 0


# --------------------------------------------------------------------------- #
# S3                                                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def s3_backend_and_bucket(aws_endpoint: str, aws_region: str):  # type: ignore[no-untyped-def]
    _require_boto3()
    import boto3  # type: ignore[import-untyped]
    from loop_control_plane.aws_backends import S3Config, build_s3_object_store

    bucket = f"loop-it-{uuid.uuid4().hex[:8]}"
    raw = boto3.client("s3", region_name=aws_region, endpoint_url=aws_endpoint)
    raw.create_bucket(Bucket=bucket)

    config = S3Config(
        bucket=bucket,
        region=aws_region,
        endpoint_url=aws_endpoint,
    )
    return build_s3_object_store(config), bucket


def test_live_s3_put_get_round_trip(s3_backend_and_bucket) -> None:  # type: ignore[no-untyped-def]
    store, _ = s3_backend_and_bucket
    payload = b"hello live s3"
    store.put("greeting.txt", payload, content_type="text/plain")
    assert store.get("greeting.txt") == payload


def test_live_s3_signed_url_format(s3_backend_and_bucket) -> None:  # type: ignore[no-untyped-def]
    store, _ = s3_backend_and_bucket
    url = store.signed_url("any-key", ttl_seconds=120)
    # localstack returns a presigned URL prefixed with the endpoint
    assert "X-Amz-Signature" in url or "AWSAccessKeyId" in url


def test_live_s3_multipart_upload(s3_backend_and_bucket) -> None:  # type: ignore[no-untyped-def]
    store, _ = s3_backend_and_bucket
    upload_id = store.create_multipart_upload("multipart/big.bin")
    # S3 requires parts ≥5 MiB except the last; localstack relaxes this
    # so we can use small parts. In real AWS you'd pad each part.
    # NB: skip real-AWS multipart with tiny parts; localstack only.
    pad = b"x" * (5 * 1024 * 1024)
    store.upload_part(upload_id, 1, pad)
    store.upload_part(upload_id, 2, b"tail")
    body = store.complete_multipart_upload(upload_id, "multipart/big.bin")
    assert body == pad + b"tail"
