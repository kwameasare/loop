"""Tests for loop_control_plane.siem_webhook — S633."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

import pytest

from loop_control_plane.audit_log import AuditEvent, AuditLogger, InMemoryAuditStore
from loop_control_plane.siem_webhook import (
    SiemWebhookConfig,
    SiemWebhookDispatcher,
    WebhookDeliveryError,
    _sign,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WS = uuid.uuid4()
SECRET = "supersecret"


def make_event(workspace_id: uuid.UUID = WS) -> AuditEvent:
    store = InMemoryAuditStore()
    logger = AuditLogger(store)
    return logger.record(
        workspace_id=workspace_id,
        action="api_key:create",
        resource_type="api_key",
    )


def make_dispatcher(
    url: str = "https://siem.example.com/ingest",
    secret: str = SECRET,
    calls: list[tuple[str, bytes, dict]] | None = None,
    status: int = 200,
    target: str = "generic",
) -> tuple[SiemWebhookDispatcher, list[tuple[str, bytes, dict]]]:
    captured: list[tuple[str, bytes, dict]] = [] if calls is None else calls

    def send_fn(u: str, body: bytes, headers: dict) -> int:
        captured.append((u, body, headers))
        return status

    store = InMemoryAuditStore()
    dispatcher = SiemWebhookDispatcher(store=store, registry={}, send_fn=send_fn)
    dispatcher.register(
        SiemWebhookConfig(
            workspace_id=WS,
            url=url,
            secret=secret,
            target=target,  # type: ignore[arg-type]
        )
    )
    return dispatcher, captured


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


class TestSigning:
    def test_sign_returns_hmac_sha256_prefix(self) -> None:
        sig = _sign(b"hello", "secret")
        assert sig.startswith("hmac-sha256=")

    def test_sign_is_verifiable(self) -> None:
        body = b'{"id":"abc"}'
        sig = _sign(body, "mysecret")
        hex_part = sig.removeprefix("hmac-sha256=")
        expected = hmac.new(b"mysecret", body, hashlib.sha256).hexdigest()
        assert hex_part == expected

    def test_sign_different_secrets_produce_different_signatures(self) -> None:
        body = b"data"
        assert _sign(body, "s1") != _sign(body, "s2")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_stores_config(self) -> None:
        d, _ = make_dispatcher()
        assert d.get_config(WS) is not None

    def test_unregister_removes_config(self) -> None:
        d, _ = make_dispatcher()
        d.unregister(WS)
        assert d.get_config(WS) is None

    def test_get_config_unknown_workspace_returns_none(self) -> None:
        d, _ = make_dispatcher()
        assert d.get_config(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


class TestDelivery:
    def test_deliver_posts_json_payload(self) -> None:
        event = make_event()
        d, calls = make_dispatcher()
        d.deliver(event)
        assert len(calls) == 1
        url, body, headers = calls[0]
        assert url == "https://siem.example.com/ingest"
        parsed = json.loads(body)
        assert parsed["id"] == str(event.id)
        assert parsed["action"] == "api_key:create"

    def test_deliver_sets_signature_header(self) -> None:
        event = make_event()
        d, calls = make_dispatcher()
        d.deliver(event)
        _, body, headers = calls[0]
        expected_sig = _sign(body, SECRET)
        assert headers["x-loop-signature-256"] == expected_sig

    def test_deliver_sets_workspace_header(self) -> None:
        event = make_event()
        d, calls = make_dispatcher()
        d.deliver(event)
        _, _, headers = calls[0]
        assert headers["x-loop-workspace-id"] == str(WS)

    def test_deliver_noop_when_no_config(self) -> None:
        event = make_event()
        calls: list = []
        store = InMemoryAuditStore()
        d = SiemWebhookDispatcher(
            store=store,
            registry={},
            send_fn=lambda u, b, h: calls.append((u, b, h)) or 200,  # type: ignore[return-value]
        )
        d.deliver(event)  # should not call send_fn
        assert calls == []

    def test_deliver_noop_when_disabled(self) -> None:
        event = make_event()
        calls: list = []

        def send_fn(u: str, b: bytes, h: dict) -> int:
            calls.append(True)
            return 200

        store = InMemoryAuditStore()
        d = SiemWebhookDispatcher(store=store, registry={}, send_fn=send_fn)
        d.register(
            SiemWebhookConfig(
                workspace_id=WS,
                url="https://example.com",
                secret="x",
                enabled=False,
            )
        )
        d.deliver(event)
        assert calls == []

    def test_deliver_raises_on_non_2xx(self) -> None:
        event = make_event()
        d, _ = make_dispatcher(status=500)
        with pytest.raises(WebhookDeliveryError) as exc_info:
            d.deliver(event)
        assert exc_info.value.status_code == 500
        assert exc_info.value.event_id == event.id

    def test_deliver_raises_on_4xx(self) -> None:
        event = make_event()
        d, _ = make_dispatcher(status=401)
        with pytest.raises(WebhookDeliveryError) as exc_info:
            d.deliver(event)
        assert exc_info.value.status_code == 401

    def test_payload_includes_entry_hash(self) -> None:
        event = make_event()
        d, calls = make_dispatcher()
        d.deliver(event)
        _, body, _ = calls[0]
        parsed = json.loads(body)
        assert "entry_hash" in parsed


# ---------------------------------------------------------------------------
# Back-fill
# ---------------------------------------------------------------------------


class TestBackfill:
    def test_backfill_delivers_all_stored_events(self) -> None:
        store = InMemoryAuditStore()
        logger = AuditLogger(store)
        for _ in range(3):
            logger.record(workspace_id=WS, action="api_key:create", resource_type="api_key")

        calls: list = []

        def send_fn(u: str, b: bytes, h: dict) -> int:
            calls.append(json.loads(b))
            return 200

        d = SiemWebhookDispatcher(store=store, registry={}, send_fn=send_fn)
        d.register(SiemWebhookConfig(workspace_id=WS, url="https://example.com", secret="s"))
        count = d.backfill(WS)
        assert count == 3
        assert len(calls) == 3

    def test_backfill_returns_zero_for_empty_workspace(self) -> None:
        store = InMemoryAuditStore()
        d, _ = make_dispatcher()
        d.store = store
        count = d.backfill(WS)
        assert count == 0

    def test_backfill_stops_on_first_failure(self) -> None:
        store = InMemoryAuditStore()
        logger = AuditLogger(store)
        for _ in range(3):
            logger.record(workspace_id=WS, action="api_key:create", resource_type="api_key")

        call_count = 0

        def send_fn(u: str, b: bytes, h: dict) -> int:
            nonlocal call_count
            call_count += 1
            return 500 if call_count >= 2 else 200

        d = SiemWebhookDispatcher(store=store, registry={}, send_fn=send_fn)
        d.register(SiemWebhookConfig(workspace_id=WS, url="https://example.com", secret="s"))
        with pytest.raises(WebhookDeliveryError):
            d.backfill(WS)
        # Only 2 calls made (1 success + 1 failure that raises)
        assert call_count == 2

    def test_backfill_only_delivers_workspace_events(self) -> None:
        store = InMemoryAuditStore()
        logger = AuditLogger(store)
        other_ws = uuid.uuid4()
        logger.record(workspace_id=WS, action="api_key:create", resource_type="api_key")
        logger.record(workspace_id=other_ws, action="agent:deploy", resource_type="agent")

        calls: list = []

        def send_fn(u: str, b: bytes, h: dict) -> int:
            calls.append(json.loads(b))
            return 200

        d = SiemWebhookDispatcher(store=store, registry={}, send_fn=send_fn)
        d.register(SiemWebhookConfig(workspace_id=WS, url="https://example.com", secret="s"))
        d.backfill(WS)
        assert len(calls) == 1
        assert calls[0]["workspace_id"] == str(WS)
