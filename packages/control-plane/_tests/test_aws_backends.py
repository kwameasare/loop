"""Tests for the boto3-backed AWS KMS + S3 backends (S905).

Hermetic — no boto3 / network. Stubs at :class:`_StubKmsClient` and
:class:`_StubS3Client` mimic the subset of the boto3 surface that
:class:`AwsKmsBackend` and :class:`S3ObjectStore` call.

Live integration tests against `localstack` are gated on
``LOOP_AWS_INTEGRATION=1`` in
``tests/test_aws_backends_integration.py``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from loop_control_plane.aws_backends import (
    AwsKmsBackend,
    AwsKmsConfig,
    S3Client,
    S3Config,
    S3ObjectStore,
    build_aws_kms_backend,
    build_s3_object_store,
)
from loop_control_plane.kms import KMSError, build_kms_backend
from loop_control_plane.object_store import (
    ObjectStoreError,
    build_object_store_backend,
)

# --------------------------------------------------------------------------- #
# Stub KMS client                                                             #
# --------------------------------------------------------------------------- #


@dataclass
class _StubKmsClient:
    """In-memory mimic of ``boto3.client('kms')``. Encryption is a
    deterministic XOR so encrypt/decrypt round-trips."""

    _keys: dict[str, bytes] = field(default_factory=dict[str, bytes])
    _rotation_dates: dict[str, datetime] = field(default_factory=dict[str, datetime])
    raise_on_next: BaseException | None = None

    def _key_material(self, key_id: str) -> bytes:
        if key_id not in self._keys:
            self._keys[key_id] = hashlib.sha256(key_id.encode()).digest()
            self._rotation_dates[key_id] = datetime(2026, 1, 1, tzinfo=UTC)
        return self._keys[key_id]

    @staticmethod
    def _xor(data: bytes, keystream: bytes) -> bytes:
        return bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(data))

    def _maybe_raise(self) -> None:
        if self.raise_on_next is not None:
            exc = self.raise_on_next
            self.raise_on_next = None
            raise exc

    def encrypt(self, *, KeyId: str, Plaintext: bytes) -> dict[str, Any]:
        self._maybe_raise()
        return {"CiphertextBlob": self._xor(Plaintext, self._key_material(KeyId))}

    def decrypt(self, *, CiphertextBlob: bytes, KeyId: str) -> dict[str, Any]:
        self._maybe_raise()
        return {"Plaintext": self._xor(CiphertextBlob, self._key_material(KeyId))}

    def generate_data_key(self, *, KeyId: str, KeySpec: str) -> dict[str, Any]:
        self._maybe_raise()
        del KeySpec
        plaintext = hashlib.sha256(f"datakey:{KeyId}".encode()).digest()
        ciphertext = self._xor(plaintext, self._key_material(KeyId))
        return {"Plaintext": plaintext, "CiphertextBlob": ciphertext}

    def update_key_description(self, *, KeyId: str, Description: str) -> dict[str, Any]:
        self._maybe_raise()
        del KeyId, Description
        return {}

    def describe_key(self, *, KeyId: str) -> dict[str, Any]:
        self._maybe_raise()
        self._key_material(KeyId)  # ensure rotation date is seeded
        return {
            "KeyMetadata": {
                "RotationDate": self._rotation_dates[KeyId],
                "CreationDate": self._rotation_dates[KeyId],
            }
        }

    def force_rotation(self, key_id: str) -> None:
        """Test helper: bump the simulated rotation date by 1 second."""
        prev = self._rotation_dates.get(key_id, datetime(2026, 1, 1, tzinfo=UTC))
        from datetime import timedelta

        self._rotation_dates[key_id] = prev + timedelta(seconds=1)

    def sign(
        self,
        *,
        KeyId: str,
        Message: bytes,
        MessageType: str,
        SigningAlgorithm: str,
    ) -> dict[str, Any]:
        self._maybe_raise()
        del MessageType, SigningAlgorithm
        sig = hashlib.sha256(self._key_material(KeyId) + Message).digest()
        return {"Signature": sig}


# --------------------------------------------------------------------------- #
# Stub S3 client                                                              #
# --------------------------------------------------------------------------- #


class _Stream:
    """Mimic boto3's StreamingBody."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body


@dataclass
class _StubS3Client(S3Client):
    objects: dict[tuple[str, str], bytes] = field(default_factory=dict[tuple[str, str], bytes])
    multipart_parts: dict[str, dict[int, bytes]] = field(
        default_factory=dict[str, dict[int, bytes]]
    )
    upload_counter: int = 0
    raise_on_next: BaseException | None = None
    last_signed_url_args: dict[str, Any] | None = None

    def _maybe_raise(self) -> None:
        if self.raise_on_next is not None:
            exc = self.raise_on_next
            self.raise_on_next = None
            raise exc

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str | None = None,
    ) -> dict[str, Any]:
        self._maybe_raise()
        del ContentType
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": '"' + hashlib.md5(Body).hexdigest() + '"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._maybe_raise()
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"NoSuchKey: {Bucket}/{Key}")
        return {"Body": _Stream(self.objects[(Bucket, Key)])}

    def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, Any],
        ExpiresIn: int,
    ) -> str:
        self._maybe_raise()
        self.last_signed_url_args = {
            "method": ClientMethod,
            "params": Params,
            "expires": ExpiresIn,
        }
        return (
            f"https://s3.amazonaws.com/{Params['Bucket']}/{Params['Key']}"
            f"?X-Amz-Expires={ExpiresIn}&X-Amz-Method={ClientMethod}"
        )

    def create_multipart_upload(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._maybe_raise()
        del Bucket, Key
        self.upload_counter += 1
        upload_id = f"upload-{self.upload_counter}"
        self.multipart_parts[upload_id] = {}
        return {"UploadId": upload_id}

    def upload_part(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        PartNumber: int,
        Body: bytes,
    ) -> dict[str, Any]:
        self._maybe_raise()
        del Bucket, Key
        if UploadId not in self.multipart_parts:
            raise KeyError(f"NoSuchUpload: {UploadId}")
        self.multipart_parts[UploadId][PartNumber] = bytes(Body)
        etag = '"' + hashlib.md5(Body).hexdigest() + '"'
        return {"ETag": etag}

    def complete_multipart_upload(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        MultipartUpload: dict[str, Any],
    ) -> dict[str, Any]:
        self._maybe_raise()
        del MultipartUpload
        if UploadId not in self.multipart_parts:
            raise KeyError(f"NoSuchUpload: {UploadId}")
        body = b"".join(
            self.multipart_parts[UploadId][n] for n in sorted(self.multipart_parts[UploadId])
        )
        self.objects[(Bucket, Key)] = body
        del self.multipart_parts[UploadId]
        return {}


# --------------------------------------------------------------------------- #
# AwsKmsConfig validation                                                     #
# --------------------------------------------------------------------------- #


def test_kms_config_rejects_empty_region() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        AwsKmsConfig(region="")


def test_kms_config_rejects_relative_endpoint() -> None:
    with pytest.raises(ValueError, match="must start with http"):
        AwsKmsConfig(region="us-east-1", endpoint_url="kms.local")


def test_kms_config_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="must be > 0"):
        AwsKmsConfig(region="us-east-1", timeout_seconds=0)


# --------------------------------------------------------------------------- #
# AwsKmsBackend round-trips                                                   #
# --------------------------------------------------------------------------- #


@pytest.fixture
def kms() -> tuple[AwsKmsBackend, _StubKmsClient]:
    config = AwsKmsConfig(region="us-east-1")
    client = _StubKmsClient()
    return AwsKmsBackend(client=client, config=config), client


def test_kms_encrypt_decrypt_roundtrips(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, _ = kms
    plaintext = b"top secret"
    ciphertext = backend.encrypt(key_ref="key-1", plaintext=plaintext)
    assert backend.decrypt(key_ref="key-1", ciphertext=ciphertext) == plaintext


def test_kms_generate_data_key(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, _ = kms
    plaintext, ciphertext = backend.generate_data_key(key_ref="key-2")
    assert len(plaintext) == 32
    # Round-trip through decrypt
    assert backend.decrypt(key_ref="key-2", ciphertext=ciphertext) == plaintext


def test_kms_sign_returns_bytes(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, _ = kms
    sig = backend.sign(key_ref="key-3", payload=b"audit-event")
    assert isinstance(sig, bytes)
    assert len(sig) == 32  # sha256


def test_kms_rotate_returns_int_epoch(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, client = kms
    backend.encrypt(key_ref="key-4", plaintext=b"x")
    v1 = backend.rotate(key_ref="key-4")
    assert isinstance(v1, int)
    client.force_rotation("key-4")
    v2 = backend.rotate(key_ref="key-4")
    assert v2 > v1


def test_kms_empty_key_ref_rejected(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, _ = kms
    with pytest.raises(KMSError, match="non-empty"):
        backend.encrypt(key_ref="", plaintext=b"x")


def test_kms_upstream_failure_wraps(
    kms: tuple[AwsKmsBackend, _StubKmsClient],
) -> None:
    backend, client = kms
    client.raise_on_next = RuntimeError("AccessDenied")
    with pytest.raises(KMSError, match="encrypt failed.*AccessDenied"):
        backend.encrypt(key_ref="k", plaintext=b"x")


def test_kms_factory_via_kms_module() -> None:
    config = AwsKmsConfig(region="us-east-1")
    client = _StubKmsClient()
    kms = build_kms_backend("aws_kms", config=config, client=client)
    assert isinstance(kms, AwsKmsBackend)
    assert kms.backend == "aws_kms"


def test_kms_factory_rejects_wrong_config_type() -> None:
    with pytest.raises(KMSError, match="AwsKmsConfig"):
        build_kms_backend("aws_kms", config="not-a-config")  # type: ignore[arg-type]


def test_kms_factory_falls_back_to_inmemory_without_config() -> None:
    kms = build_kms_backend("aws_kms")
    assert kms.backend == "aws_kms"
    assert not isinstance(kms, AwsKmsBackend)


def test_build_aws_kms_backend_with_custom_client() -> None:
    config = AwsKmsConfig(region="us-east-1")
    client = _StubKmsClient()
    kms = build_aws_kms_backend(config, client=client)
    assert isinstance(kms, AwsKmsBackend)
    assert kms.client is client


# --------------------------------------------------------------------------- #
# S3Config validation                                                         #
# --------------------------------------------------------------------------- #


def test_s3_config_rejects_empty_bucket() -> None:
    with pytest.raises(ValueError, match="bucket"):
        S3Config(bucket="", region="us-east-1")


def test_s3_config_rejects_empty_region() -> None:
    with pytest.raises(ValueError, match="region"):
        S3Config(bucket="my-bucket", region="")


def test_s3_config_rejects_relative_endpoint() -> None:
    with pytest.raises(ValueError, match="must start with http"):
        S3Config(bucket="my-bucket", region="us-east-1", endpoint_url="s3.local")


# --------------------------------------------------------------------------- #
# S3ObjectStore round-trips                                                   #
# --------------------------------------------------------------------------- #


@pytest.fixture
def s3() -> tuple[S3ObjectStore, _StubS3Client]:
    config = S3Config(bucket="loop-objects", region="us-east-1")
    client = _StubS3Client()
    return S3ObjectStore(client=client, config=config), client


def test_s3_put_get_roundtrips(s3: tuple[S3ObjectStore, _StubS3Client]) -> None:
    store, _ = s3
    store.put("path/to/object.bin", b"hello world", content_type="application/octet-stream")
    assert store.get("path/to/object.bin") == b"hello world"


def test_s3_get_missing_key_raises(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, _ = s3
    with pytest.raises(ObjectStoreError, match="get failed"):
        store.get("does-not-exist")


def test_s3_signed_url_get(s3: tuple[S3ObjectStore, _StubS3Client]) -> None:
    store, client = s3
    url = store.signed_url("photo.jpg", ttl_seconds=60)
    assert url.startswith("https://s3.amazonaws.com/loop-objects/photo.jpg")
    assert client.last_signed_url_args is not None
    assert client.last_signed_url_args["method"] == "get_object"
    assert client.last_signed_url_args["expires"] == 60


def test_s3_signed_url_put(s3: tuple[S3ObjectStore, _StubS3Client]) -> None:
    store, client = s3
    url = store.signed_url("upload.bin", ttl_seconds=120, method="PUT")
    assert "X-Amz-Method=put_object" in url
    assert client.last_signed_url_args is not None
    assert client.last_signed_url_args["method"] == "put_object"


def test_s3_signed_url_rejects_bad_method(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, _ = s3
    with pytest.raises(ObjectStoreError, match="unsupported"):
        store.signed_url("k", ttl_seconds=10, method="POST")


def test_s3_signed_url_rejects_zero_ttl(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, _ = s3
    with pytest.raises(ObjectStoreError, match="must be positive"):
        store.signed_url("k", ttl_seconds=0)


def test_s3_multipart_upload(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, _ = s3
    upload_id = store.create_multipart_upload("big-object")
    etag1 = store.upload_part(upload_id, 1, b"hello ")
    etag2 = store.upload_part(upload_id, 2, b"world")
    assert etag1 != etag2
    body = store.complete_multipart_upload(upload_id, "big-object")
    assert body == b"hello world"
    # Subsequent calls to the same upload_id are rejected.
    with pytest.raises(ObjectStoreError, match="unknown multipart upload"):
        store.upload_part(upload_id, 3, b"!")


def test_s3_upload_part_rejects_zero_part_number(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, _ = s3
    upload_id = store.create_multipart_upload("k")
    with pytest.raises(ObjectStoreError, match="part_number must be"):
        store.upload_part(upload_id, 0, b"x")


def test_s3_factory_via_object_store_module() -> None:
    config = S3Config(bucket="loop-objects", region="us-east-1")
    client = _StubS3Client()
    store = build_object_store_backend("s3", config=config, client=client)
    assert isinstance(store, S3ObjectStore)


def test_s3_factory_rejects_wrong_config_type() -> None:
    with pytest.raises(ObjectStoreError, match="S3Config"):
        build_object_store_backend("s3", config="bad")  # type: ignore[arg-type]


def test_s3_factory_falls_back_to_inmemory_without_config() -> None:
    store = build_object_store_backend("s3")
    assert store.backend == "s3"
    assert not isinstance(store, S3ObjectStore)


def test_build_s3_object_store_with_custom_client() -> None:
    config = S3Config(bucket="loop-objects", region="us-east-1")
    client = _StubS3Client()
    store = build_s3_object_store(config, client=client)
    assert isinstance(store, S3ObjectStore)
    assert store.client is client


def test_s3_upstream_failure_wraps(
    s3: tuple[S3ObjectStore, _StubS3Client],
) -> None:
    store, client = s3
    client.raise_on_next = RuntimeError("AccessDenied")
    with pytest.raises(ObjectStoreError, match="put failed"):
        store.put("k", b"x")
