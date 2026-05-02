from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote, urlencode

OBJECT_STORE_BACKENDS = ("s3", "azure-blob", "gcs", "oss", "swift", "minio")


class ObjectStoreError(RuntimeError): ...


class ObjectStore(Protocol):
    backend: str

    def put(self, key: str, body: bytes, *, content_type: str | None = None) -> None: ...
    def get(self, key: str) -> bytes: ...
    def signed_url(self, key: str, *, ttl_seconds: int, method: str = "GET") -> str: ...
    def create_multipart_upload(self, key: str) -> str: ...
    def upload_part(self, upload_id: str, part_number: int, body: bytes) -> str: ...
    def complete_multipart_upload(self, upload_id: str, key: str) -> bytes: ...


@dataclass
class InMemoryObjectStore:
    backend: str
    endpoint: str
    secret: bytes = b"loop-objectstore-contract"
    _objects: dict[str, bytes] = field(default_factory=dict[str, bytes])
    _uploads: dict[str, dict[int, bytes]] = field(default_factory=dict[str, dict[int, bytes]])

    def put(self, key: str, body: bytes, *, content_type: str | None = None) -> None:
        _ = content_type
        self._objects[key] = bytes(body)

    def get(self, key: str) -> bytes:
        if key not in self._objects:
            raise ObjectStoreError(f"{self.backend} object not found: {key}")
        return self._objects[key]

    def signed_url(self, key: str, *, ttl_seconds: int, method: str = "GET") -> str:
        if ttl_seconds <= 0:
            raise ObjectStoreError("signed URL ttl_seconds must be positive")
        expires = int(time.time()) + ttl_seconds
        verb = method.upper()
        payload = f"{self.backend}:{verb}:{key}:{expires}".encode()
        signature = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        return f"{self.endpoint}/{quote(key)}?{urlencode({'expires': expires, 'method': verb, 'signature': signature})}"

    def create_multipart_upload(self, key: str) -> str:
        seed = f"{self.backend}:{key}:{len(self._uploads)}".encode()
        upload_id = hashlib.sha256(seed).hexdigest()[:24]
        self._uploads[upload_id] = {}
        return upload_id

    def upload_part(self, upload_id: str, part_number: int, body: bytes) -> str:
        if part_number < 1:
            raise ObjectStoreError("part_number must be >= 1")
        self._upload(upload_id)[part_number] = bytes(body)
        return hashlib.sha256(body).hexdigest()

    def complete_multipart_upload(self, upload_id: str, key: str) -> bytes:
        parts = self._upload(upload_id)
        if not parts:
            raise ObjectStoreError("multipart upload has no parts")
        body = b"".join(parts[index] for index in sorted(parts))
        del self._uploads[upload_id]
        self.put(key, body)
        return body

    def _upload(self, upload_id: str) -> dict[int, bytes]:
        if upload_id not in self._uploads:
            raise ObjectStoreError(f"unknown multipart upload: {upload_id}")
        return self._uploads[upload_id]


def build_object_store_backend(backend: str) -> ObjectStore:
    if backend not in OBJECT_STORE_BACKENDS:
        raise ObjectStoreError(f"unsupported object store backend: {backend}")
    return InMemoryObjectStore(backend=backend, endpoint=f"https://{backend}.objects.loop.test")
