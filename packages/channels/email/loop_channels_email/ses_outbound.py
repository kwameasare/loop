"""SES outbound + DKIM signer (S514).

Outbound delivery uses SES SendRawEmail. We *always* DKIM-sign locally
before handing the blob to SES — this lets us migrate off SES without
moving DKIM keys, and keeps the canonical signed-bytes deterministic
for tests.

The DKIM implementation here is the simplified relaxed/relaxed
canonicalisation defined in RFC 6376 §3.4. The actual cryptographic
signature is delegated to a ``Signer`` Protocol so unit tests can
inject a deterministic stub without depending on ``cryptography``.
"""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

CRLF = b"\r\n"


class DkimError(ValueError):
    """DKIM signing failed (missing headers, bad domain, signer error)."""


@runtime_checkable
class Signer(Protocol):
    """Wraps an asymmetric signer (RSA-SHA256 / Ed25519-SHA256)."""

    @property
    def algorithm(self) -> str: ...

    def sign(self, data: bytes) -> bytes: ...


@dataclass(frozen=True, slots=True)
class DkimConfig:
    """Per-domain signing config."""

    domain: str
    selector: str
    headers_to_sign: tuple[str, ...] = (
        "from",
        "to",
        "subject",
        "date",
        "message-id",
    )

    def __post_init__(self) -> None:
        if not self.domain or "." not in self.domain:
            raise DkimError(f"invalid domain {self.domain!r}")
        if not self.selector:
            raise DkimError("selector required")
        if "from" not in self.headers_to_sign:
            raise DkimError("'from' must be in headers_to_sign")


def canonicalise_header_relaxed(name: str, value: str) -> bytes:
    """RFC 6376 §3.4.2 relaxed header canonicalisation."""
    name_lower = name.lower().strip()
    # Unfold + collapse internal whitespace to single spaces; trim trailing.
    folded = re.sub(r"\s+", " ", value.replace("\r\n", " ")).strip()
    return f"{name_lower}:{folded}".encode() + CRLF


def canonicalise_body_relaxed(body: bytes) -> bytes:
    """RFC 6376 §3.4.4 relaxed body canonicalisation.

    Steps: trim trailing whitespace per line, collapse internal runs
    of whitespace, drop trailing empty lines, ensure body ends with
    exactly one CRLF.
    """
    if not body:
        return CRLF
    text = body.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n")
    out_lines: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        out_lines.append(line.rstrip(" \t"))
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    return ("\r\n".join(out_lines) + "\r\n").encode("utf-8")


def body_hash(body: bytes) -> str:
    """Compute the ``bh=`` parameter (base64 SHA-256 of canonical body)."""
    digest = hashlib.sha256(canonicalise_body_relaxed(body)).digest()
    return base64.b64encode(digest).decode("ascii")


def build_signature_header(
    *,
    config: DkimConfig,
    headers: dict[str, str],
    body: bytes,
    signer: Signer,
) -> str:
    """Return the value of the ``DKIM-Signature`` header to prepend."""
    missing = [h for h in config.headers_to_sign if h not in {k.lower() for k in headers}]
    if missing:
        raise DkimError(f"missing required headers: {missing}")
    bh = body_hash(body)
    h_list = ":".join(config.headers_to_sign)
    # Build the header sans ``b=`` value first; sign over that.
    base = (
        f"v=1; a={signer.algorithm}; c=relaxed/relaxed; "
        f"d={config.domain}; s={config.selector}; h={h_list}; "
        f"bh={bh}; b="
    )
    canonical_headers = b""
    headers_lower = {k.lower(): v for k, v in headers.items()}
    for name in config.headers_to_sign:
        canonical_headers += canonicalise_header_relaxed(name, headers_lower[name])
    canonical_headers += canonicalise_header_relaxed("DKIM-Signature", base)
    # Strip the trailing CRLF before signing the DKIM-Signature header
    # itself, per RFC 6376 §3.7 step 2.
    canonical = canonical_headers[: -len(CRLF)]
    sig = signer.sign(canonical)
    b64 = base64.b64encode(sig).decode("ascii")
    return base + b64


@dataclass(slots=True)
class SesOutboundSender:
    """Build a signed RFC-822 blob and ship it via SES."""

    config: DkimConfig
    signer: Signer
    send_raw_email: Callable[[bytes], Awaitable[str]]  # returns SES message id

    async def send(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> str:
        sig_value = build_signature_header(
            config=self.config, headers=headers, body=body, signer=self.signer
        )
        all_headers: list[bytes] = [f"DKIM-Signature: {sig_value}".encode()]
        for name, value in headers.items():
            all_headers.append(f"{name}: {value}".encode())
        blob = CRLF.join(all_headers) + CRLF + CRLF + body
        return await self.send_raw_email(blob)


__all__ = [
    "DkimConfig",
    "DkimError",
    "SesOutboundSender",
    "Signer",
    "body_hash",
    "build_signature_header",
    "canonicalise_body_relaxed",
    "canonicalise_header_relaxed",
]
