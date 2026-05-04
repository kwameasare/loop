"""Hermetic SNS signature verification tests (P0.5d).

We mint our own RSA cert + signature so the test runs without a network
trip to AWS sns.* domains.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID
from loop_channels_email.sns_verify import (
    SnsSignatureError,
    verify_sns_signature,
)


def _make_self_signed_cert() -> tuple[rsa.RSAPrivateKey, bytes]:
    """Generate a self-signed RSA cert for SNS verification tests."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "sns.us-east-1.amazonaws.com")]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(priv.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2024, 1, 1, tzinfo=timezone.utc))
        .not_valid_after(datetime(2030, 1, 1, tzinfo=timezone.utc))
        .sign(priv, hashes.SHA256())
    )
    return priv, cert.public_bytes(Encoding.PEM)


def _sign_v2(priv: rsa.RSAPrivateKey, string_to_sign: bytes) -> str:
    sig = priv.sign(string_to_sign, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def _string_to_sign_for_notification(message: dict) -> bytes:
    keys = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
    parts: list[str] = []
    for k in keys:
        v = message.get(k)
        if v is None:
            if k == "Subject":
                continue
            raise ValueError(f"missing {k}")
        parts.append(k)
        parts.append(str(v))
    return ("\n".join(parts) + "\n").encode("utf-8")


@pytest.fixture(scope="module")
def cert_pair() -> tuple[rsa.RSAPrivateKey, bytes]:
    return _make_self_signed_cert()


def _ts_now_iso() -> str:
    """Use a frozen 'now' so tests are reproducible."""
    return "2026-05-04T10:00:00.000Z"


def _frozen_now() -> float:
    # Same instant as _ts_now_iso
    return datetime.fromisoformat("2026-05-04T10:00:00+00:00").timestamp()


def test_verify_accepts_valid_v2_notification(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "abc123",
        "TopicArn": "arn:aws:sns:us-east-1:111122223333:loop-ses-inbound",
        "Subject": "test",
        "Message": "hello",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    verify_sns_signature(
        message=msg,
        fetch_signing_cert=lambda url: cert_pem,
        allowed_topic_arns=("arn:aws:sns:us-east-1:111122223333:loop-ses-inbound",),
        now=_frozen_now(),
    )


def test_verify_rejects_v1_when_v2_required(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    """v1 (SHA1) was deprecated in 2022."""
    _priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:topic",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "1",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
        "Signature": "ignored",
    }
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg,
            fetch_signing_cert=lambda url: cert_pem,
            now=_frozen_now(),
        )


def test_verify_rejects_signing_cert_off_aws_domain(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    """The whole point of host-pinning: an attacker who controls
    `attacker.example` could otherwise serve their own cert."""
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:topic",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://attacker.example/sns-cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg,
            fetch_signing_cert=lambda url: cert_pem,
            now=_frozen_now(),
        )


def test_verify_rejects_http_signing_cert(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:topic",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "http://sns.us-east-1.amazonaws.com/cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg,
            fetch_signing_cert=lambda url: cert_pem,
            now=_frozen_now(),
        )


def test_verify_rejects_topic_not_in_allowlist(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:9:other-topic",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg,
            fetch_signing_cert=lambda url: cert_pem,
            allowed_topic_arns=("arn:aws:sns:us-east-1:1:loop-ses-inbound",),
            now=_frozen_now(),
        )


def test_verify_rejects_tampered_message(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:t",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    msg["Message"] = "evil-payload"  # tamper after signing
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg, fetch_signing_cert=lambda url: cert_pem, now=_frozen_now()
        )


def test_verify_rejects_old_timestamp(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    """Even a valid signature must be rejected if the timestamp is
    far older than the skew window — replay defense."""
    priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:t",
        "Message": "hi",
        "Timestamp": "2026-05-04T08:00:00.000Z",  # 2 hours ago
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
    }
    msg["Signature"] = _sign_v2(priv, _string_to_sign_for_notification(msg))
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg,
            fetch_signing_cert=lambda url: cert_pem,
            now=_frozen_now(),  # 2 hours later
        )


def test_verify_rejects_unknown_message_type(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    _priv, cert_pem = cert_pair
    msg = {
        "Type": "WeirdType",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:t",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
        "Signature": "anything",
    }
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg, fetch_signing_cert=lambda url: cert_pem, now=_frozen_now()
        )


def test_verify_supports_subscription_confirmation(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    priv, cert_pem = cert_pair
    msg = {
        "Type": "SubscriptionConfirmation",
        "MessageId": "x",
        "Token": "a-very-long-confirmation-token",
        "TopicArn": "arn:aws:sns:us-east-1:1:t",
        "Message": "You have chosen to subscribe...",
        "SubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&...",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
    }
    keys = [
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ]
    parts: list[str] = []
    for k in keys:
        parts.append(k)
        parts.append(str(msg[k]))
    sts = ("\n".join(parts) + "\n").encode("utf-8")
    msg["Signature"] = _sign_v2(priv, sts)

    verify_sns_signature(
        message=msg, fetch_signing_cert=lambda url: cert_pem, now=_frozen_now()
    )


def test_verify_rejects_malformed_signature(
    cert_pair: tuple[rsa.RSAPrivateKey, bytes],
) -> None:
    _priv, cert_pem = cert_pair
    msg = {
        "Type": "Notification",
        "MessageId": "x",
        "TopicArn": "arn:aws:sns:us-east-1:1:t",
        "Message": "hi",
        "Timestamp": _ts_now_iso(),
        "SignatureVersion": "2",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
        "Signature": "!!!not-base64!!!",
    }
    with pytest.raises(SnsSignatureError):
        verify_sns_signature(
            message=msg, fetch_signing_cert=lambda url: cert_pem, now=_frozen_now()
        )
