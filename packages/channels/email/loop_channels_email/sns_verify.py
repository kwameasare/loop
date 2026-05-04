"""AWS SNS message-signature verification.

Closes P0.5d from the prod-readiness audit. SES is configured to write
inbound MIME blobs to S3 and emit an SNS notification listing the new
objects. The receiving service consumes these SNS notifications via an
HTTPS endpoint. Without verifying the SNS message signature, anyone can
post an SNS-shaped JSON body to the public webhook URL — pointing at
attacker-controlled S3 keys — and trick the inbound pipeline into
ingesting fake emails.

See: https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html

Verification recipe (per AWS docs):

1. Confirm `SignatureVersion` is `1` (SHA1) or `2` (SHA256). We require
   `2` because v1 was deprecated in 2022 — operators on v1 must opt in.
2. Build the canonical `StringToSign`:
   - For Notification messages: `Message`, `MessageId`, `Subject`
     (only if present), `Timestamp`, `TopicArn`, `Type`.
   - For SubscriptionConfirmation/UnsubscribeConfirmation:
     `Message`, `MessageId`, `SubscribeURL`, `Timestamp`, `Token`,
     `TopicArn`, `Type`.
   Each field is appended as `key\nvalue\n`.
3. Pull the signing certificate from `SigningCertURL` (must be on
   `*.amazonaws.com`).
4. Verify RSA-SHA256 (or SHA1) signature.
5. Validate `Timestamp` is recent (default 1h window).
6. Validate `TopicArn` matches an allow-list.

Implementation
==============
* The `fetch_signing_cert` callable is operator-injected so the host
  service owns the HTTPS GET + caching. Tests inject a stub.
* `SigningCertURL` host is validated against
  `*.sns.<region>.amazonaws.com` to defend against a compromised DNS
  / open redirect.
* All failure modes raise the same `SnsSignatureError` with a generic
  message — defense in depth.
"""

from __future__ import annotations

import base64
import re
import time
from collections.abc import Callable
from typing import Any, Final
from urllib.parse import urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS: Final[int] = 3600
SIGNING_CERT_HOST_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^sns\.[a-z0-9-]+\.amazonaws\.com$"
)


class SnsSignatureError(ValueError):
    """Raised when an inbound SNS notification fails verification."""


# (PEM bytes,) -> ok flag is the implementation detail; the public API
# is just "give me the signing cert PEM bytes for this URL".
SigningCertFetcher = Callable[[str], bytes]


def _string_to_sign(message: dict[str, Any]) -> bytes:
    """Build the canonical StringToSign per AWS SNS spec."""
    msg_type = message.get("Type")
    if msg_type == "Notification":
        keys = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
    elif msg_type in ("SubscriptionConfirmation", "UnsubscribeConfirmation"):
        keys = [
            "Message",
            "MessageId",
            "SubscribeURL",
            "Timestamp",
            "Token",
            "TopicArn",
            "Type",
        ]
    else:
        raise SnsSignatureError("invalid sns message")
    parts: list[str] = []
    for key in keys:
        value = message.get(key)
        if value is None:
            # Subject is only present on some Notifications; omit it
            # entirely from the StringToSign if absent (matches AWS
            # spec "Skip if not present").
            if key == "Subject":
                continue
            raise SnsSignatureError("invalid sns message")
        parts.append(key)
        parts.append(str(value))
    return ("\n".join(parts) + "\n").encode("utf-8")


def _validate_signing_cert_url(url: str) -> None:
    """Reject signing-cert URLs that aren't on the SNS service domain.

    AWS sample malicious-input: SNS sends `SigningCertURL` pointing at
    attacker.example which serves a cert paired with the attacker's
    private key. We hard-pin the host pattern to defeat this.
    """
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise SnsSignatureError("invalid sns message") from exc
    if parsed.scheme != "https":
        raise SnsSignatureError("invalid sns message")
    host = (parsed.hostname or "").lower()
    if not SIGNING_CERT_HOST_PATTERN.match(host):
        raise SnsSignatureError("invalid sns message")


def verify_sns_signature(
    *,
    message: dict[str, Any],
    fetch_signing_cert: SigningCertFetcher,
    allowed_topic_arns: tuple[str, ...] | None = None,
    max_timestamp_skew_seconds: int = DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS,
    require_v2: bool = True,
    now: float | None = None,
) -> None:
    """Verify an SNS HTTPS-delivered message.

    Raises :class:`SnsSignatureError` on any failure; returns normally
    on success.

    Parameters
    ----------
    message
        Parsed JSON body posted by SNS. Must include `Type`,
        `Signature`, `SigningCertURL`, `SignatureVersion`, etc.
    fetch_signing_cert
        Callable that fetches the PEM-encoded signing certificate
        bytes for the URL. The host service owns caching and HTTP.
    allowed_topic_arns
        Optional allow-list. When provided, `TopicArn` must match
        one of the listed ARNs exactly. Strongly recommended.
    max_timestamp_skew_seconds
        Reject if |now - Timestamp| > this. Default 1h.
    require_v2
        Reject `SignatureVersion=1` (SHA1, deprecated 2022). Default True.
    now
        Override for tests.
    """
    if not isinstance(message, dict):
        raise SnsSignatureError("invalid sns message")

    sig_version = message.get("SignatureVersion")
    if sig_version not in ("1", "2"):
        raise SnsSignatureError("invalid sns message")
    if require_v2 and sig_version != "2":
        raise SnsSignatureError("invalid sns message")

    signature_b64 = message.get("Signature")
    cert_url = message.get("SigningCertURL") or message.get("SigningCertUrl")
    if not isinstance(signature_b64, str) or not isinstance(cert_url, str):
        raise SnsSignatureError("invalid sns message")
    _validate_signing_cert_url(cert_url)

    timestamp = message.get("Timestamp")
    if not isinstance(timestamp, str):
        raise SnsSignatureError("invalid sns message")
    try:
        # ISO 8601 with 'Z' suffix (e.g. "2026-05-04T10:30:00.000Z")
        from datetime import datetime

        ts_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ts_epoch = ts_dt.timestamp()
    except (TypeError, ValueError) as exc:
        raise SnsSignatureError("invalid sns message") from exc
    current = now if now is not None else time.time()
    if abs(current - ts_epoch) > max_timestamp_skew_seconds:
        raise SnsSignatureError("invalid sns message")

    if allowed_topic_arns is not None:
        topic_arn = message.get("TopicArn")
        if topic_arn not in allowed_topic_arns:
            raise SnsSignatureError("invalid sns message")

    string_to_sign = _string_to_sign(message)

    try:
        signature = base64.b64decode(signature_b64)
    except (TypeError, ValueError) as exc:
        raise SnsSignatureError("invalid sns message") from exc

    try:
        cert_pem = fetch_signing_cert(cert_url)
    except Exception as exc:  # pragma: no cover (host-owned)
        raise SnsSignatureError("invalid sns message") from exc

    try:
        cert = load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
    except (ValueError, TypeError) as exc:
        raise SnsSignatureError("invalid sns message") from exc

    hash_algorithm = hashes.SHA256() if sig_version == "2" else hashes.SHA1()
    try:
        public_key.verify(  # type: ignore[union-attr]
            signature,
            string_to_sign,
            padding.PKCS1v15(),
            hash_algorithm,
        )
    except InvalidSignature as exc:
        raise SnsSignatureError("invalid sns message") from exc
    except Exception as exc:
        raise SnsSignatureError("invalid sns message") from exc


__all__ = [
    "DEFAULT_MAX_TIMESTAMP_SKEW_SECONDS",
    "SigningCertFetcher",
    "SnsSignatureError",
    "verify_sns_signature",
]
