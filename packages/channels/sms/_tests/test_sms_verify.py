"""Hermetic tests for Twilio webhook signature verification (P0.5b).

We compute expected signatures from Twilio's documented canonicalisation
rule (URL + sorted form fields concatenated as key+value) so the tests
match what Twilio's libraries produce on the wire.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest
from loop_channels_sms.verify import (
    TwilioSignatureError,
    verify_twilio_signature,
)


def _sign_form(auth_token: str, url: str, form: dict[str, str]) -> str:
    payload = url
    for k in sorted(form):
        payload += k + form[k]
    digest = hmac.new(
        auth_token.encode(), payload.encode(), hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _sign_json(auth_token: str, url: str, body: bytes) -> str:
    digest = hmac.new(
        auth_token.encode(), url.encode() + body, hashlib.sha1
    ).digest()
    return base64.b64encode(digest).decode("ascii")


# ---------------------------------------------------------------------- #
# Form-encoded happy/sad paths                                            #
# ---------------------------------------------------------------------- #


def test_verify_form_accepts_valid_signature() -> None:
    auth = "secret-token"
    url = "https://example.com/twilio/sms"
    form = {"From": "+15551234567", "Body": "hi", "To": "+15557654321"}
    sig = _sign_form(auth, url, form)
    verify_twilio_signature(
        auth_token=auth, url=url, signature_header=sig, form_fields=form
    )


def test_verify_form_rejects_tampered_field() -> None:
    auth = "secret-token"
    url = "https://example.com/twilio/sms"
    form = {"From": "+15551234567", "Body": "hi"}
    sig = _sign_form(auth, url, form)
    tampered = dict(form)
    tampered["Body"] = "evil"
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth, url=url, signature_header=sig, form_fields=tampered
        )


def test_verify_form_rejects_wrong_url() -> None:
    """The full request URL is part of the signed payload — so a
    different URL with the same form should fail."""
    auth = "secret-token"
    url1 = "https://example.com/twilio/sms"
    url2 = "https://example.com/twilio/voice"
    form = {"From": "+15551234567", "Body": "hi"}
    sig = _sign_form(auth, url1, form)
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth, url=url2, signature_header=sig, form_fields=form
        )


def test_verify_form_rejects_wrong_token() -> None:
    auth = "secret-token"
    url = "https://example.com/twilio/sms"
    form = {"From": "+15551234567"}
    sig = _sign_form(auth, url, form)
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token="other-token",
            url=url,
            signature_header=sig,
            form_fields=form,
        )


def test_verify_form_uses_canonical_sort_order() -> None:
    """Field-ordering must not affect the signature: dict iteration
    order in callers may differ from Twilio's canonical sort, so we
    must sort internally."""
    auth = "secret-token"
    url = "https://example.com/twilio/sms"
    # Same fields, different insertion order.
    form_a = {"Body": "hi", "From": "+1", "To": "+2"}
    form_b = {"To": "+2", "From": "+1", "Body": "hi"}
    sig = _sign_form(auth, url, form_a)
    verify_twilio_signature(
        auth_token=auth, url=url, signature_header=sig, form_fields=form_b
    )


# ---------------------------------------------------------------------- #
# JSON path                                                               #
# ---------------------------------------------------------------------- #


def test_verify_json_accepts_valid_signature() -> None:
    auth = "secret-token"
    url = "https://example.com/notify"
    body = b'{"event": "delivered"}'
    sig = _sign_json(auth, url, body)
    verify_twilio_signature(
        auth_token=auth, url=url, signature_header=sig, body=body
    )


def test_verify_json_rejects_tampered_body() -> None:
    auth = "secret-token"
    url = "https://example.com/notify"
    body = b'{"event": "delivered"}'
    sig = _sign_json(auth, url, body)
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth, url=url, signature_header=sig, body=body + b"x"
        )


def test_verify_rejects_when_both_form_and_body_provided() -> None:
    """Caller must pick one; passing both is a programming error and
    we fail loud rather than silently signing one or the other."""
    auth = "t"
    url = "https://example.com/x"
    sig = _sign_form(auth, url, {"a": "b"})
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth,
            url=url,
            signature_header=sig,
            form_fields={"a": "b"},
            body=b"{}",
        )


def test_verify_rejects_when_neither_form_nor_body_provided() -> None:
    auth = "t"
    url = "https://example.com/x"
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth, url=url, signature_header="anything"
        )


# ---------------------------------------------------------------------- #
# Replay window (opt-in, requires operator-stamped timestamp)             #
# ---------------------------------------------------------------------- #


def test_verify_rejects_replay_outside_skew_window() -> None:
    """Defense-in-depth: when the operator's edge proxy stamps the
    request with a timestamp, gate on it so a replayed capture from
    yesterday doesn't trigger an agent run today."""
    auth = "t"
    url = "https://example.com/x"
    form = {"a": "b"}
    sig = _sign_form(auth, url, form)
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth,
            url=url,
            signature_header=sig,
            form_fields=form,
            timestamp="1700000000",  # ~Nov 2023
            now=1700000000 + 3600,  # 1h later, > 600s default window
        )


def test_verify_accepts_replay_inside_skew_window() -> None:
    auth = "t"
    url = "https://example.com/x"
    form = {"a": "b"}
    sig = _sign_form(auth, url, form)
    verify_twilio_signature(
        auth_token=auth,
        url=url,
        signature_header=sig,
        form_fields=form,
        timestamp="1700000000",
        now=1700000000 + 60,  # 1 minute later, well within window
    )


# ---------------------------------------------------------------------- #
# Defensive guards                                                        #
# ---------------------------------------------------------------------- #


def test_verify_rejects_oversized_json_body() -> None:
    auth = "t"
    url = "https://example.com/x"
    body = b"x" * (3 * 1024 * 1024)
    sig = _sign_json(auth, url, body)
    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            auth_token=auth, url=url, signature_header=sig, body=body
        )


def test_verify_rejects_empty_token_url_or_signature() -> None:
    for kwargs in (
        {"auth_token": "", "url": "https://x", "signature_header": "s", "form_fields": {}},
        {"auth_token": "t", "url": "", "signature_header": "s", "form_fields": {}},
        {"auth_token": "t", "url": "https://x", "signature_header": "", "form_fields": {}},
    ):
        with pytest.raises(TwilioSignatureError):
            verify_twilio_signature(**kwargs)  # type: ignore[arg-type]


def test_verify_constant_time_compare_used() -> None:
    """Lightly assert that we're not using `==` for string compare
    (would leak secret via timing). Indirect: we patch hmac.compare_digest
    and confirm it gets called."""
    import loop_channels_sms.verify as v

    called: list[tuple[bytes, bytes]] = []
    real = v.hmac.compare_digest

    def spy(a: bytes | str, b: bytes | str) -> bool:
        called.append((bytes(a, "utf-8") if isinstance(a, str) else a,
                       bytes(b, "utf-8") if isinstance(b, str) else b))
        return real(a, b)

    v.hmac.compare_digest = spy  # type: ignore[assignment]
    try:
        auth = "t"
        url = "https://example.com/x"
        form = {"a": "b"}
        sig = _sign_form(auth, url, form)
        verify_twilio_signature(
            auth_token=auth, url=url, signature_header=sig, form_fields=form
        )
        assert called, "expected hmac.compare_digest to be invoked"
    finally:
        v.hmac.compare_digest = real  # type: ignore[assignment]
