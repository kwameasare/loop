"""S776 ObjectStore parity suite across cloud and OSS backends."""

from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

import pytest
from loop_control_plane.object_store import (
    OBJECT_STORE_BACKENDS,
    ObjectStoreError,
    build_object_store_backend,
)


@pytest.mark.parametrize("backend", OBJECT_STORE_BACKENDS)
def test_object_store_backends_share_put_get_and_signed_url_contract(backend: str) -> None:
    store = build_object_store_backend(backend)
    store.put("workspace-a/transcript.json", b'{"ok":true}', content_type="application/json")

    assert store.backend == backend
    assert store.get("workspace-a/transcript.json") == b'{"ok":true}'

    signed = store.signed_url("workspace-a/transcript.json", ttl_seconds=300, method="put")
    parsed = urlparse(signed)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == f"{backend}.objects.loop.test"
    assert parsed.path == "/workspace-a/transcript.json"
    assert query["method"] == ["PUT"]
    assert len(query["signature"][0]) == 64
    assert int(query["expires"][0]) > int(time.time())


@pytest.mark.parametrize("backend", OBJECT_STORE_BACKENDS)
def test_object_store_backends_share_multipart_contract(backend: str) -> None:
    store = build_object_store_backend(backend)
    upload_id = store.create_multipart_upload("bundles/agent.tar")

    etag_2 = store.upload_part(upload_id, 2, b"world")
    etag_1 = store.upload_part(upload_id, 1, b"hello ")
    body = store.complete_multipart_upload(upload_id, "bundles/agent.tar")

    assert etag_1 != etag_2
    assert body == b"hello world"
    assert store.get("bundles/agent.tar") == b"hello world"


def test_object_store_contract_rejects_unsupported_or_invalid_operations() -> None:
    store = build_object_store_backend("s3")
    with pytest.raises(ObjectStoreError, match="unsupported"):
        build_object_store_backend("dropbox")
    with pytest.raises(ObjectStoreError, match="not found"):
        store.get("missing")
    with pytest.raises(ObjectStoreError, match="ttl_seconds"):
        store.signed_url("missing", ttl_seconds=0)
    with pytest.raises(ObjectStoreError, match="part_number"):
        store.upload_part(store.create_multipart_upload("parts"), 0, b"x")
    with pytest.raises(ObjectStoreError, match="unknown multipart"):
        store.complete_multipart_upload("missing-upload", "parts")
    empty_upload = store.create_multipart_upload("empty")
    with pytest.raises(ObjectStoreError, match="no parts"):
        store.complete_multipart_upload(empty_upload, "empty")
