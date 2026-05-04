"""Hermetic inbound DKIM verification tests (P0.5e).

We use dkimpy itself to sign test MIME blobs (so signing matches what
real senders produce on the wire), then assert our wrapper reaches the
right verdict.
"""

from __future__ import annotations

import dkim
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from loop_channels_email.dkim_inbound import (
    InboundDkimStatus,
    verify_dkim_inbound,
)


def _make_test_keys() -> tuple[bytes, bytes]:
    """Generate a 1024-bit RSA keypair (small for speed; production
    DKIM uses 2048-bit). Returns (private_pem, public_b64_for_dns)."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = priv.public_key()
    pub_der = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    import base64

    pub_b64 = base64.b64encode(pub_der).decode("ascii")
    return priv_pem, pub_b64.encode("ascii")


def _sign(message: bytes, priv_pem: bytes, *, domain: bytes, selector: bytes) -> bytes:
    """Use dkimpy to mint a signed MIME blob."""
    sig = dkim.sign(
        message=message,
        selector=selector,
        domain=domain,
        privkey=priv_pem,
        signature_algorithm=b"rsa-sha256",
    )
    # dkim.sign returns the DKIM-Signature header(s); prepend to body.
    return sig + message


@pytest.fixture(scope="module")
def keypair() -> tuple[bytes, bytes]:
    return _make_test_keys()


def _dns_lookup_for(public_key_b64: bytes) -> object:
    """Return a DNS lookup callable that serves the public key for any
    name (suitable for tests that only have one signer)."""

    def lookup(name: str) -> list[str]:
        return [f"v=DKIM1; k=rsa; p={public_key_b64.decode('ascii')}"]

    return lookup


_VALID_MIME = (
    b"From: sender@example.com\r\n"
    b"To: bot@loop.local\r\n"
    b"Subject: hi\r\n"
    b"Date: Mon, 04 May 2026 10:00:00 +0000\r\n"
    b"Message-ID: <abc@example.com>\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"hello world\r\n"
)


def test_verify_accepts_valid_signature(keypair: tuple[bytes, bytes]) -> None:
    priv_pem, pub_b64 = keypair
    signed = _sign(_VALID_MIME, priv_pem, domain=b"example.com", selector=b"sel1")
    result = verify_dkim_inbound(signed, dns_txt_lookup=_dns_lookup_for(pub_b64))  # type: ignore[arg-type]
    assert result.status == InboundDkimStatus.PASS, result.reason
    assert result.domain == "example.com"
    assert result.selector == "sel1"


def test_verify_rejects_tampered_body(keypair: tuple[bytes, bytes]) -> None:
    priv_pem, pub_b64 = keypair
    signed = _sign(_VALID_MIME, priv_pem, domain=b"example.com", selector=b"sel1")
    tampered = signed.replace(b"hello world", b"evil payload")
    result = verify_dkim_inbound(tampered, dns_txt_lookup=_dns_lookup_for(pub_b64))  # type: ignore[arg-type]
    assert result.status == InboundDkimStatus.FAIL, result.reason


def test_verify_returns_fail_when_no_signature_and_required() -> None:
    """No DKIM-Signature header at all + require_signature=True → FAIL."""
    result = verify_dkim_inbound(
        _VALID_MIME, dns_txt_lookup=lambda _name: []
    )  # type: ignore[arg-type]
    assert result.status == InboundDkimStatus.FAIL
    assert "no DKIM-Signature" in result.reason


def test_verify_returns_none_when_no_signature_and_not_required() -> None:
    """For trusted internal relays callers can opt out with
    require_signature=False."""
    result = verify_dkim_inbound(
        _VALID_MIME,
        dns_txt_lookup=lambda _name: [],  # type: ignore[arg-type]
        require_signature=False,
    )
    assert result.status == InboundDkimStatus.NONE


def test_verify_rejects_when_dns_returns_no_record(
    keypair: tuple[bytes, bytes],
) -> None:
    """If the signing key isn't published in DNS at the selector, we
    can't trust the signature — FAIL (or ERROR depending on dkimpy)."""
    priv_pem, _ = keypair
    signed = _sign(_VALID_MIME, priv_pem, domain=b"example.com", selector=b"sel1")
    result = verify_dkim_inbound(signed, dns_txt_lookup=lambda _name: [])  # type: ignore[arg-type]
    # dkimpy raises KeyFormatError or similar; we map to FAIL or ERROR.
    assert result.status in {InboundDkimStatus.FAIL, InboundDkimStatus.ERROR}


def test_verify_rejects_oversized_message() -> None:
    """Defensive size cap prevents OOM on a malicious 1 GB blob."""
    huge = b"x" * (51 * 1024 * 1024)  # 51 MiB > 50 MiB cap
    result = verify_dkim_inbound(huge, dns_txt_lookup=lambda _name: [])  # type: ignore[arg-type]
    assert result.status == InboundDkimStatus.ERROR
    assert "too large" in result.reason


def test_verify_rejects_non_bytes_input() -> None:
    result = verify_dkim_inbound(
        "not bytes",  # type: ignore[arg-type]
        dns_txt_lookup=lambda _name: [],
    )
    assert result.status == InboundDkimStatus.ERROR


def test_verify_extracts_domain_and_selector_from_signature(
    keypair: tuple[bytes, bytes],
) -> None:
    priv_pem, pub_b64 = keypair
    signed = _sign(
        _VALID_MIME, priv_pem, domain=b"loop-test.com", selector=b"sel99"
    )
    result = verify_dkim_inbound(signed, dns_txt_lookup=_dns_lookup_for(pub_b64))  # type: ignore[arg-type]
    assert result.domain == "loop-test.com"
    assert result.selector == "sel99"
