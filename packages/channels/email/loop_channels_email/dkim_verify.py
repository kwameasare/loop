"""SPF + DKIM verification for studio domain-connect (S516).

When a workspace connects a custom sending domain, we run a
verification probe to confirm ``v=spf1 include:amazonses.com -all``
is present and that DKIM keys are published. This module is the
pure-functional verifier; DNS lookups are injected so the verifier
runs in unit tests without the network.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

DnsLookup = Callable[[str, str], Awaitable[list[str]]]
"""(name, record_type) -> list of TXT/CNAME values."""


class SpfStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SOFTFAIL = "softfail"
    NEUTRAL = "neutral"
    NONE = "none"


class DkimStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class SpfResult:
    status: SpfStatus
    record: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class DkimResult:
    status: DkimStatus
    selector: str
    record: str | None
    reason: str


_SPF_RE = re.compile(r"v=spf1\b", re.IGNORECASE)
_QUALIFIER_RE = re.compile(r"\s([+\-~?])all\b")


async def verify_spf(domain: str, *, dns: DnsLookup) -> SpfResult:
    if not domain:
        raise ValueError("domain required")
    txts = await dns(domain, "TXT")
    spf = next((t for t in txts if _SPF_RE.search(t)), None)
    if spf is None:
        return SpfResult(SpfStatus.NONE, None, "no v=spf1 TXT record")
    m = _QUALIFIER_RE.search(" " + spf)
    if not m:
        return SpfResult(SpfStatus.NEUTRAL, spf, "no -all qualifier present")
    qualifier = m.group(1)
    status = {
        "-": SpfStatus.PASS,
        "~": SpfStatus.SOFTFAIL,
        "?": SpfStatus.NEUTRAL,
        "+": SpfStatus.FAIL,  # +all is misconfigured
    }[qualifier]
    reason = {
        SpfStatus.PASS: "strict -all qualifier",
        SpfStatus.SOFTFAIL: "~all qualifier (soft)",
        SpfStatus.NEUTRAL: "?all qualifier",
        SpfStatus.FAIL: "+all qualifier (open relay)",
    }[status]
    return SpfResult(status, spf, reason)


_DKIM_FIELD_RE = re.compile(r"(?P<key>[a-z]+)=(?P<value>[^;]+)", re.IGNORECASE)


async def verify_dkim(domain: str, selector: str, *, dns: DnsLookup) -> DkimResult:
    if not selector:
        raise ValueError("selector required")
    name = f"{selector}._domainkey.{domain}"
    txts = await dns(name, "TXT")
    if not txts:
        return DkimResult(DkimStatus.NONE, selector, None, f"no TXT at {name}")
    record = txts[0]
    fields = {m.group("key").lower(): m.group("value").strip() for m in _DKIM_FIELD_RE.finditer(record)}
    if fields.get("v", "DKIM1") != "DKIM1":
        return DkimResult(DkimStatus.FAIL, selector, record, "v= not DKIM1")
    if not fields.get("p"):
        return DkimResult(DkimStatus.FAIL, selector, record, "p= public key missing")
    return DkimResult(DkimStatus.PASS, selector, record, "DKIM1 record with non-empty p=")


__all__ = [
    "DkimResult",
    "DkimStatus",
    "DnsLookup",
    "SpfResult",
    "SpfStatus",
    "verify_dkim",
    "verify_spf",
]
