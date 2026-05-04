"""Hermetic tests for ed25519 verification of Discord webhooks.

Discord's interactions API signs every webhook with ed25519 over
``timestamp || body``. The receiving service MUST verify before
parsing or replying — otherwise anyone with the public key (which
isn't a secret) can spoof inbound interactions.

These tests use deterministic ed25519 key material so they're
reproducible and don't require any test fixtures.
"""

from __future__ import annotations

import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from loop_channels_discord.verify import (
    DiscordSignatureError,
    verify_discord_signature,
)


def _fresh_keypair() -> tuple[bytes, bytes, Ed25519PrivateKey]:
    """Generate a deterministic test keypair (returns priv-bytes, pub-bytes, priv-obj)."""
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=Encoding.Raw, format=PublicFormat.Raw
    )
    return priv_bytes, pub_bytes, priv


def _signed(
    body: bytes, priv: Ed25519PrivateKey, ts: int | None = None
) -> tuple[str, str]:
    """Return (signature_hex, timestamp_str) for body+priv."""
    timestamp = str(ts if ts is not None else int(time.time()))
    sig = priv.sign(timestamp.encode("utf-8") + body)
    return sig.hex(), timestamp


def test_verify_accepts_valid_signature() -> None:
    _, pub_bytes, priv = _fresh_keypair()
    body = b'{"type": 1}'  # PING interaction
    sig_hex, ts = _signed(body, priv)
    # Should not raise.
    verify_discord_signature(
        body=body, signature_hex=sig_hex, timestamp=ts, public_key=pub_bytes
    )


def test_verify_accepts_hex_public_key() -> None:
    """Discord's developer dashboard shows the key as hex; both
    raw bytes and hex string must work."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b'{"type": 1}'
    sig_hex, ts = _signed(body, priv)
    verify_discord_signature(
        body=body, signature_hex=sig_hex, timestamp=ts, public_key=pub_bytes.hex()
    )


def test_verify_rejects_tampered_body() -> None:
    """Even one byte changed in the body must fail verification."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b'{"type": 2, "data": {"name": "ask"}}'
    sig_hex, ts = _signed(body, priv)
    tampered = body + b" "
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=tampered, signature_hex=sig_hex, timestamp=ts, public_key=pub_bytes
        )


def test_verify_rejects_signature_for_different_key() -> None:
    """Re-using a signature against a different application's public
    key must fail (cross-key replay)."""
    _, _, priv = _fresh_keypair()
    _, other_pub, _ = _fresh_keypair()
    body = b"{}"
    sig_hex, ts = _signed(body, priv)
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=body, signature_hex=sig_hex, timestamp=ts, public_key=other_pub
        )


def test_verify_rejects_signature_with_wrong_timestamp() -> None:
    """Discord includes the timestamp in the signed message; bumping
    it after signing must fail."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b"{}"
    sig_hex, _ = _signed(body, priv, ts=1700000000)
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=body,
            signature_hex=sig_hex,
            timestamp="1700000001",
            public_key=pub_bytes,
            now=1700000001.0,
        )


def test_verify_rejects_replay_outside_window() -> None:
    """Even with a valid signature, a timestamp older than
    max_skew_seconds is a replay vector."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b"{}"
    # Sign with timestamp from 1 hour ago
    old_ts = int(time.time()) - 3600
    sig_hex, ts = _signed(body, priv, ts=old_ts)
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=body,
            signature_hex=sig_hex,
            timestamp=ts,
            public_key=pub_bytes,
            max_skew_seconds=300,  # 5 min default
        )


def test_verify_rejects_malformed_signature_hex() -> None:
    _, pub_bytes, _ = _fresh_keypair()
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=b"{}",
            signature_hex="not-hex-at-all",
            timestamp=str(int(time.time())),
            public_key=pub_bytes,
        )


def test_verify_rejects_short_signature() -> None:
    """A 32-byte signature would fail ed25519 verification anyway,
    but we reject it up-front so attackers can't tell which check
    failed."""
    _, pub_bytes, _ = _fresh_keypair()
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=b"{}",
            signature_hex="ab" * 32,  # 32 bytes, not 64
            timestamp=str(int(time.time())),
            public_key=pub_bytes,
        )


def test_verify_rejects_malformed_public_key() -> None:
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=b"{}",
            signature_hex="aa" * 64,
            timestamp=str(int(time.time())),
            public_key="not-hex-at-all",
        )


def test_verify_rejects_oversized_body() -> None:
    """Defensive cap so a malicious caller can't OOM us by sending
    multi-GB request bodies through the verifier."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b"x" * (3 * 1024 * 1024)  # 3 MiB > MAX_BODY_BYTES
    sig_hex, ts = _signed(body, priv)
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=body, signature_hex=sig_hex, timestamp=ts, public_key=pub_bytes
        )


def test_verify_rejects_non_integer_timestamp() -> None:
    _, pub_bytes, priv = _fresh_keypair()
    body = b"{}"
    sig_hex, _ = _signed(body, priv)
    with pytest.raises(DiscordSignatureError):
        verify_discord_signature(
            body=body,
            signature_hex=sig_hex,
            timestamp="not-a-number",
            public_key=pub_bytes,
        )


def test_verify_error_message_does_not_leak_which_check_failed() -> None:
    """Defense-in-depth: the public exception message must be
    consistent across causes so attackers can't time- or text-attack
    individual checks."""
    _, pub_bytes, priv = _fresh_keypair()
    body = b"{}"
    sig_hex, ts = _signed(body, priv)

    # Tampered body
    msg_a = ""
    try:
        verify_discord_signature(
            body=body + b"x", signature_hex=sig_hex, timestamp=ts, public_key=pub_bytes
        )
    except DiscordSignatureError as exc:
        msg_a = str(exc)

    # Wrong key
    _, other_pub, _ = _fresh_keypair()
    msg_b = ""
    try:
        verify_discord_signature(
            body=body, signature_hex=sig_hex, timestamp=ts, public_key=other_pub
        )
    except DiscordSignatureError as exc:
        msg_b = str(exc)

    # Both must be the bland "invalid signature" string.
    assert msg_a == "invalid signature"
    assert msg_b == "invalid signature"
