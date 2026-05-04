"""Tests for the cross-channel idempotency primitives (P0.5g)."""

from __future__ import annotations

import pytest
from loop_channels_core.idempotency import (
    MemoryIdempotencyStore,
    make_dedup_key,
    provider_event_id_for_discord,
    provider_event_id_for_email,
    provider_event_id_for_rcs,
    provider_event_id_for_slack,
    provider_event_id_for_teams,
    provider_event_id_for_telegram,
    provider_event_id_for_twilio,
    provider_event_id_for_web,
    provider_event_id_for_whatsapp,
)

# --------------------------------------------------------------------------- #
# Store contract                                                              #
# --------------------------------------------------------------------------- #


def test_memory_store_first_claim_succeeds() -> None:
    store = MemoryIdempotencyStore()
    assert store.claim("slack:event-1") is True


def test_memory_store_second_claim_fails() -> None:
    store = MemoryIdempotencyStore()
    store.claim("slack:event-1")
    assert store.claim("slack:event-1") is False


def test_memory_store_different_keys_dont_collide() -> None:
    store = MemoryIdempotencyStore()
    assert store.claim("slack:event-1") is True
    assert store.claim("slack:event-2") is True
    assert store.claim("whatsapp:wamid.xxx") is True


def test_memory_store_expires_after_ttl() -> None:
    """A retry that lands AFTER the TTL must be re-accepted (not a
    real retry; either the dedup window was misconfigured or this is
    a genuinely new event)."""
    fake_now = [1000.0]

    def now() -> float:
        return fake_now[0]

    store = MemoryIdempotencyStore(_now=now)
    assert store.claim("k1", ttl_seconds=60) is True
    fake_now[0] = 1030.0  # 30s later — still in window
    assert store.claim("k1", ttl_seconds=60) is False
    fake_now[0] = 1100.0  # 100s later — past TTL
    assert store.claim("k1", ttl_seconds=60) is True


def test_make_dedup_key_namespaces_per_channel() -> None:
    assert make_dedup_key("slack", "ev-1") == "slack:ev-1"
    assert make_dedup_key("whatsapp", "ev-1") == "whatsapp:ev-1"
    # Same provider id under different channels = different key
    assert make_dedup_key("slack", "ev-1") != make_dedup_key("whatsapp", "ev-1")


def test_make_dedup_key_rejects_empty() -> None:
    with pytest.raises(ValueError):
        make_dedup_key("", "x")
    with pytest.raises(ValueError):
        make_dedup_key("slack", "")


# --------------------------------------------------------------------------- #
# Per-channel extractors                                                      #
# --------------------------------------------------------------------------- #


def test_slack_extractor_uses_event_id() -> None:
    assert (
        provider_event_id_for_slack({"event_id": "Ev123ABC", "team_id": "T1"})
        == "Ev123ABC"
    )


def test_slack_extractor_falls_back_to_event_ts() -> None:
    payload = {"event": {"ts": "1700000000.000123", "type": "message"}}
    assert provider_event_id_for_slack(payload).startswith("event-ts-")


def test_slack_extractor_falls_back_to_content_hash() -> None:
    """A payload missing both event_id and event_ts still gets a stable
    key — same input, same key (but two different inputs differ)."""
    p1 = {"foo": "bar"}
    p2 = {"foo": "baz"}
    assert provider_event_id_for_slack(p1).startswith("ch-")
    assert provider_event_id_for_slack(p1) == provider_event_id_for_slack(p1)
    assert provider_event_id_for_slack(p1) != provider_event_id_for_slack(p2)


def test_whatsapp_extractor_finds_message_wamid() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.HBgL...",
                                    "from": "15551234567",
                                    "timestamp": "1700000000",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    assert provider_event_id_for_whatsapp(payload) == "message-wamid.HBgL..."


def test_whatsapp_extractor_finds_status_id() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {"id": "delivery-xyz", "status": "delivered"}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    assert provider_event_id_for_whatsapp(payload) == "statuse-delivery-xyz"


def test_discord_extractor_uses_id() -> None:
    assert provider_event_id_for_discord({"id": "snowflake-1234"}) == "snowflake-1234"


def test_telegram_extractor_uses_update_id() -> None:
    assert provider_event_id_for_telegram({"update_id": 42}) == "update-42"


def test_twilio_extractor_uses_message_sid() -> None:
    assert (
        provider_event_id_for_twilio({"MessageSid": "SM" + "x" * 32})
        == f"sid-SM{'x' * 32}"
    )


def test_teams_extractor_combines_conversation_and_id() -> None:
    payload = {"id": "act-1", "conversation": {"id": "conv-9"}}
    assert provider_event_id_for_teams(payload) == "conv-9:act-1"


def test_email_extractor_uses_ses_messageId() -> None:
    payload = {
        "Records": [
            {"ses": {"mail": {"messageId": "ses-msg-9"}}}
        ]
    }
    assert provider_event_id_for_email(payload) == "ses-ses-msg-9"


def test_email_extractor_falls_back_to_mime_message_id() -> None:
    payload = {"Message-ID": "<abc@example.com>"}
    assert provider_event_id_for_email(payload) == "mime-<abc@example.com>"


def test_rcs_extractor_uses_messageId() -> None:
    assert provider_event_id_for_rcs({"messageId": "uuid-1"}) == "rcs-uuid-1"


def test_web_extractor_uses_clientMessageId() -> None:
    assert provider_event_id_for_web({"clientMessageId": "client-uuid"}) == "web-client-uuid"


# --------------------------------------------------------------------------- #
# Realistic end-to-end retry scenario                                         #
# --------------------------------------------------------------------------- #


def test_retry_scenario_dedups_duplicate_inbound() -> None:
    """The full picture: same Meta WAMID delivered twice → only the
    first claim wins, the second is recognised as a retry."""
    store = MemoryIdempotencyStore()
    payload = {
        "entry": [
            {
                "changes": [
                    {"value": {"messages": [{"id": "wamid.X", "timestamp": "1700"}]}}
                ]
            }
        ]
    }
    eid = provider_event_id_for_whatsapp(payload)
    key = make_dedup_key("whatsapp", eid)
    assert store.claim(key) is True  # first delivery
    assert store.claim(key) is False  # retry
    assert store.claim(key) is False  # retry again
