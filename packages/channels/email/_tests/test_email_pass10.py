"""Tests for pass10 email modules (S513, S514, S516, S779)."""

from __future__ import annotations

import pytest
from loop_channels_email.dkim_verify import (
    DkimStatus,
    SpfStatus,
    verify_dkim,
    verify_spf,
)
from loop_channels_email.email_parity import (
    EmailSenderError,
    InMemoryEmailSender,
    OutboundEmail,
    run_parity,
)
from loop_channels_email.ses_inbound import (
    S3ObjectRef,
    SesInboundError,
    SesInboundIngester,
    parse_rfc822,
    parse_s3_event,
)
from loop_channels_email.ses_outbound import (
    DkimConfig,
    DkimError,
    SesOutboundSender,
    body_hash,
    build_signature_header,
    canonicalise_body_relaxed,
    canonicalise_header_relaxed,
)

# --------------------------- ses_inbound ---------------------------


def test_parse_s3_event_extracts_records():
    event = {
        "Records": [
            {"s3": {"bucket": {"name": "loop-mail"}, "object": {"key": "in/abc"}}},
            {"s3": {"bucket": {"name": "loop-mail"}, "object": {"key": "in/def"}}},
        ]
    }
    refs = parse_s3_event(event)
    assert refs == [
        S3ObjectRef(bucket="loop-mail", key="in/abc"),
        S3ObjectRef(bucket="loop-mail", key="in/def"),
    ]


def test_parse_s3_event_rejects_empty():
    with pytest.raises(SesInboundError):
        parse_s3_event({})


def test_parse_s3_event_rejects_missing_key():
    with pytest.raises(SesInboundError):
        parse_s3_event({"Records": [{"s3": {"bucket": {"name": "b"}}}]})


def test_parse_rfc822_minimal():
    blob = (
        b"From: alice@example.com\r\n"
        b"To: bob@example.com\r\n"
        b"Subject: hello\r\n"
        b"Message-ID: <abc@example.com>\r\n"
        b"\r\n"
        b"hi there\r\n"
    )
    msg = parse_rfc822(blob)
    assert msg.from_address == "alice@example.com"
    assert msg.to_addresses == ("bob@example.com",)
    assert msg.subject == "hello"
    assert msg.body_text == "hi there"
    assert msg.message_id == "<abc@example.com>"


def test_parse_rfc822_threading_headers():
    blob = (
        b"From: alice@example.com\r\n"
        b"To: bob@example.com\r\n"
        b"Subject: re\r\n"
        b"In-Reply-To: <root@example.com>\r\n"
        b"References: <root@example.com> <m1@example.com>\r\n"
        b"\r\n"
        b"reply body\r\n"
    )
    msg = parse_rfc822(blob)
    assert msg.in_reply_to == "<root@example.com>"
    assert msg.references == ("<root@example.com>", "<m1@example.com>")


def test_parse_rfc822_rejects_empty_blob():
    with pytest.raises(SesInboundError):
        parse_rfc822(b"")


def test_parse_rfc822_rejects_missing_from():
    with pytest.raises(SesInboundError):
        parse_rfc822(b"To: x@x.com\r\n\r\nbody\r\n")


@pytest.mark.asyncio
async def test_ses_ingester_round_trip():
    captured: list[str] = []

    async def fetch(ref: S3ObjectRef) -> bytes:
        captured.append(f"{ref.bucket}/{ref.key}")
        return (
            b"From: x@x.com\r\nTo: y@y.com\r\nSubject: s\r\n\r\nbody\r\n"
        )

    ing = SesInboundIngester(fetch_object=fetch)
    event = {"Records": [{"s3": {"bucket": {"name": "b"}, "object": {"key": "k"}}}]}
    out = await ing.ingest(event)
    assert len(out) == 1 and out[0].subject == "s"
    assert captured == ["b/k"]


# --------------------------- ses_outbound (DKIM) ---------------------------


class _FakeSigner:
    algorithm = "rsa-sha256"

    def sign(self, data: bytes) -> bytes:
        # Deterministic: just SHA256 of input as a stand-in signature.
        import hashlib

        return hashlib.sha256(data).digest()


def test_canonicalise_header_relaxed():
    out = canonicalise_header_relaxed("Subject", "  Hello  World  ")
    assert out == b"subject:Hello World\r\n"


def test_canonicalise_body_strips_trailing_blank_lines():
    body = b"line1\nline2  \n\n\n"
    canon = canonicalise_body_relaxed(body)
    assert canon == b"line1\r\nline2\r\n"


def test_body_hash_stable():
    h1 = body_hash(b"hello\r\n")
    h2 = body_hash(b"hello\n")  # canonicalisation aligns line endings
    assert h1 == h2


def test_build_signature_header_includes_required_tags():
    cfg = DkimConfig(domain="example.com", selector="loop1")
    headers = {
        "From": "alice@example.com",
        "To": "bob@example.com",
        "Subject": "hi",
        "Date": "Mon, 1 Jan 2024 00:00:00 +0000",
        "Message-ID": "<a@example.com>",
    }
    sig = build_signature_header(
        config=cfg, headers=headers, body=b"body\r\n", signer=_FakeSigner()
    )
    for tag in ("v=1", "a=rsa-sha256", "c=relaxed/relaxed", "d=example.com",
                "s=loop1", "h=from:to:subject:date:message-id", "bh=", "b="):
        assert tag in sig


def test_build_signature_rejects_missing_from():
    cfg = DkimConfig(domain="example.com", selector="s")
    with pytest.raises(DkimError):
        build_signature_header(
            config=cfg,
            headers={"To": "x@y.com", "Subject": "s", "Date": "d", "Message-ID": "<m>"},
            body=b"",
            signer=_FakeSigner(),
        )


def test_dkim_config_rejects_bad_domain():
    with pytest.raises(DkimError):
        DkimConfig(domain="nodot", selector="s")


@pytest.mark.asyncio
async def test_ses_outbound_signs_and_sends():
    sent: list[bytes] = []

    async def send_raw(blob: bytes) -> str:
        sent.append(blob)
        return "ses-1"

    cfg = DkimConfig(domain="example.com", selector="s")
    sender = SesOutboundSender(config=cfg, signer=_FakeSigner(), send_raw_email=send_raw)
    headers = {
        "From": "a@example.com",
        "To": "b@example.com",
        "Subject": "x",
        "Date": "Mon",
        "Message-ID": "<m>",
    }
    msg_id = await sender.send(headers=headers, body=b"hi\r\n")
    assert msg_id == "ses-1"
    assert sent and sent[0].startswith(b"DKIM-Signature: ")
    assert b"From: a@example.com" in sent[0]
    assert sent[0].endswith(b"hi\r\n")


# --------------------------- DKIM/SPF verify ---------------------------


def _dns(records: dict[str, list[str]]):
    async def lookup(name: str, rtype: str) -> list[str]:
        return list(records.get((name, rtype), []))

    return lookup


@pytest.mark.asyncio
async def test_spf_pass_with_strict_all():
    dns = _dns({("example.com", "TXT"): ["v=spf1 include:amazonses.com -all"]})
    res = await verify_spf("example.com", dns=dns)
    assert res.status is SpfStatus.PASS


@pytest.mark.asyncio
async def test_spf_softfail():
    dns = _dns({("example.com", "TXT"): ["v=spf1 include:_spf.google.com ~all"]})
    res = await verify_spf("example.com", dns=dns)
    assert res.status is SpfStatus.SOFTFAIL


@pytest.mark.asyncio
async def test_spf_no_record():
    dns = _dns({})
    res = await verify_spf("example.com", dns=dns)
    assert res.status is SpfStatus.NONE


@pytest.mark.asyncio
async def test_spf_open_relay_marked_fail():
    dns = _dns({("example.com", "TXT"): ["v=spf1 +all"]})
    res = await verify_spf("example.com", dns=dns)
    assert res.status is SpfStatus.FAIL


@pytest.mark.asyncio
async def test_dkim_pass_when_p_present():
    dns = _dns({("loop1._domainkey.example.com", "TXT"): ["v=DKIM1; k=rsa; p=ABCD"]})
    res = await verify_dkim("example.com", "loop1", dns=dns)
    assert res.status is DkimStatus.PASS


@pytest.mark.asyncio
async def test_dkim_fail_when_p_missing():
    dns = _dns({("loop1._domainkey.example.com", "TXT"): ["v=DKIM1; k=rsa"]})
    res = await verify_dkim("example.com", "loop1", dns=dns)
    assert res.status is DkimStatus.FAIL


@pytest.mark.asyncio
async def test_dkim_none_when_no_record():
    res = await verify_dkim("example.com", "missing", dns=_dns({}))
    assert res.status is DkimStatus.NONE


# --------------------------- email parity ---------------------------


@pytest.mark.asyncio
async def test_in_memory_sender_passes_parity():
    failures = await run_parity(InMemoryEmailSender)
    assert failures == []


@pytest.mark.asyncio
async def test_parity_detects_lax_backend():
    class LaxSender:
        backend_name = "lax"

        async def send(self, email):
            from loop_channels_email.email_parity import SendResult

            return SendResult(message_id="ok", backend="lax")

    failures = await run_parity(LaxSender)
    # lax accepts empty to and empty from, so parity reports 2 failures
    assert any(f.check == "rejects_empty_to" for f in failures)
    assert any(f.check == "rejects_empty_from" for f in failures)


@pytest.mark.asyncio
async def test_in_memory_sender_send_rejects_no_to():
    sender = InMemoryEmailSender()
    msg = OutboundEmail(from_address="a@b.c", to_addresses=(), subject="s", body_text="")
    with pytest.raises(EmailSenderError):
        await sender.send(msg)
