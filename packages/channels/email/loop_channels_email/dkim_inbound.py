"""DKIM verification on inbound MIME blobs.

Closes P0.5e from the prod-readiness audit. The existing
``dkim_verify.py`` only validates outbound domain-connect config; this
module verifies the DKIM-Signature header on an *inbound* MIME blob
before the runtime ingests it. Without this, an attacker who can SNS-
post a malicious S3 reference (defeated separately by P0.5d) — or who
controls any open SMTP relay that can write to our S3 bucket — could
inject "From: ceo@victim.com" emails into agent conversations.

Implementation
==============
* Wraps `dkimpy` (the canonical Python DKIM library, RFC 6376
  compliant, MIT licensed). The library handles relaxed/simple
  canonicalisation, body-hash truncation, signing-header ordering,
  and selector-based DNS TXT lookup for the public key.
* DNS lookup is operator-injectable so unit tests stay hermetic; the
  default uses dkimpy's built-in dnspython resolver.
* Returns a structured result object so callers can decide whether
  to accept (`pass`), quarantine (`fail`), or accept-without-DKIM
  (`none`) per their tenancy policy. We do NOT raise on `fail` —
  policy decisions belong to the caller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# Default body-size cap for inbound MIME so a malicious 1 GB blob
# can't OOM the verifier. Real emails are virtually always <50MB
# even with attachments; SES caps at 40MB.
MAX_INBOUND_BYTES: Final[int] = 50 * 1024 * 1024


class InboundDkimStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NONE = "none"  # no DKIM-Signature header
    ERROR = "error"  # transient (DNS / parse failure)


@dataclass(frozen=True, slots=True)
class InboundDkimResult:
    """Outcome of inbound DKIM verification.

    `domain` and `selector` are pulled from the signature header so
    callers can log / audit them even on FAIL.
    """

    status: InboundDkimStatus
    domain: str | None
    selector: str | None
    reason: str


# Operator-injectable DNS lookup. dkimpy's default uses dnspython.
DnsTxtLookup = Callable[[str], list[str]]


def _default_dns_txt_lookup() -> DnsTxtLookup:
    """Return a DnsTxtLookup that queries DNS via dnspython (the
    library dkimpy ships with). Importing here keeps the dep
    optional in test paths where caller injects."""
    import dns.resolver as _resolver

    def _lookup(name: str) -> list[str]:
        try:
            answer = _resolver.resolve(name, "TXT", lifetime=5.0)
        except Exception:
            return []
        out: list[str] = []
        for rdata in answer:
            txt_parts = []
            for s in rdata.strings:  # type: ignore[attr-defined]
                if isinstance(s, bytes):
                    txt_parts.append(s.decode("ascii", errors="replace"))
                else:
                    txt_parts.append(str(s))
            out.append("".join(txt_parts))
        return out

    return _lookup


def verify_dkim_inbound(
    raw_message: bytes,
    *,
    dns_txt_lookup: DnsTxtLookup | None = None,
    require_signature: bool = True,
    max_bytes: int = MAX_INBOUND_BYTES,
) -> InboundDkimResult:
    """Verify the DKIM signature on a raw MIME blob.

    Returns an :class:`InboundDkimResult`. We never raise on
    verification failure — the caller decides what to do based on
    `status`.

    Parameters
    ----------
    raw_message
        Raw RFC-822 bytes as delivered (do NOT re-encode).
    dns_txt_lookup
        Optional override for tests. Defaults to dnspython.
    require_signature
        If True (default), absence of a `DKIM-Signature` header is
        reported as `FAIL` (with reason "no DKIM-Signature header");
        if False, it's `NONE` so callers can accept unsigned mail
        from trusted internal relays.
    max_bytes
        Reject blobs larger than this with `ERROR`.
    """
    if not isinstance(raw_message, (bytes, bytearray)):
        return InboundDkimResult(
            status=InboundDkimStatus.ERROR,
            domain=None,
            selector=None,
            reason="raw_message must be bytes",
        )
    if len(raw_message) > max_bytes:
        return InboundDkimResult(
            status=InboundDkimStatus.ERROR,
            domain=None,
            selector=None,
            reason="message too large for DKIM verification",
        )

    # Find the signature header up-front so we can return NONE without
    # needing to call into dkimpy at all (saves a DNS round-trip).
    domain, selector = _extract_sig_dsd(raw_message)
    if not domain:
        if require_signature:
            return InboundDkimResult(
                status=InboundDkimStatus.FAIL,
                domain=None,
                selector=None,
                reason="no DKIM-Signature header",
            )
        return InboundDkimResult(
            status=InboundDkimStatus.NONE,
            domain=None,
            selector=None,
            reason="no DKIM-Signature header",
        )

    import dkim as dkimpy

    lookup = dns_txt_lookup if dns_txt_lookup is not None else _default_dns_txt_lookup()

    def _dns_txt_func(name_b: bytes, **_: object) -> bytes:
        # dkimpy passes name as bytes and expects bytes back.
        name_str = name_b.decode("ascii", errors="replace")
        records = lookup(name_str)
        # dkimpy concatenates multi-string TXTs and parses one record;
        # join with no separator (matches what the resolver returns).
        if not records:
            return b""
        return records[0].encode("ascii", errors="replace")

    try:
        ok = dkimpy.verify(raw_message, dnsfunc=_dns_txt_func)
    except dkimpy.DKIMException as exc:
        return InboundDkimResult(
            status=InboundDkimStatus.FAIL,
            domain=domain,
            selector=selector,
            reason=f"dkim error: {exc.__class__.__name__}",
        )
    except Exception as exc:
        return InboundDkimResult(
            status=InboundDkimStatus.ERROR,
            domain=domain,
            selector=selector,
            reason=f"unexpected error: {exc.__class__.__name__}",
        )

    if ok:
        return InboundDkimResult(
            status=InboundDkimStatus.PASS,
            domain=domain,
            selector=selector,
            reason="signature ok",
        )
    return InboundDkimResult(
        status=InboundDkimStatus.FAIL,
        domain=domain,
        selector=selector,
        reason="dkim signature failed verification",
    )


def _extract_sig_dsd(raw: bytes) -> tuple[str | None, str | None]:
    """Pull (d, s) tags from the first DKIM-Signature header.

    Done with a small custom scanner instead of the email module so
    we operate on the same bytes dkimpy will see (the email module's
    folded-header rewriting can drift).
    """
    # End of headers
    boundary = raw.find(b"\r\n\r\n")
    if boundary < 0:
        boundary = raw.find(b"\n\n")
    if boundary < 0:
        boundary = len(raw)
    head = raw[:boundary]

    # Unfold continuation lines (CRLF + WSP)
    unfolded = head.replace(b"\r\n ", b" ").replace(b"\r\n\t", b" ")
    unfolded = unfolded.replace(b"\n ", b" ").replace(b"\n\t", b" ")
    domain = selector = None
    for line in unfolded.split(b"\n"):
        if line.lower().startswith(b"dkim-signature:"):
            value = line.partition(b":")[2].decode("ascii", errors="replace")
            for tag in value.split(";"):
                t = tag.strip()
                if t.startswith("d="):
                    domain = t[2:].strip()
                elif t.startswith("s="):
                    selector = t[2:].strip()
            break
    return domain, selector


__all__ = [
    "MAX_INBOUND_BYTES",
    "DnsTxtLookup",
    "InboundDkimResult",
    "InboundDkimStatus",
    "verify_dkim_inbound",
]
