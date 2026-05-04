"""Hermetic Teams Bot Framework JWT verification tests (P0.5c).

We mint our own RSA keys and JWTs so the test runs without a network
trip to login.botframework.com. Production wires `fetch_jwks` to a
caching HTTPS client; the contract this test pins is "the verifier
accepts a properly-signed token and rejects everything else."
"""

from __future__ import annotations

import base64
import json
import time

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from loop_channels_teams.verify import (
    EXPECTED_ISSUER,
    TeamsAuthError,
    verify_teams_activity_jwt,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_jwks_entry(public_key: rsa.RSAPublicKey, kid: str) -> dict:
    """Build a JWK from an RSA public key (n,e form)."""
    nums = public_key.public_numbers()
    n_bytes = nums.n.to_bytes((nums.n.bit_length() + 7) // 8, "big")
    e_bytes = nums.e.to_bytes((nums.e.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "n": _b64url(n_bytes),
        "e": _b64url(e_bytes),
        "use": "sig",
    }


def _mint_jwt(
    *,
    private_key: rsa.RSAPrivateKey,
    kid: str,
    aud: str,
    iss: str = EXPECTED_ISSUER,
    service_url: str = "https://smba.trafficmanager.net/uk/",
    exp_offset: int = 3600,
    nbf_offset: int = -60,
) -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    now = int(time.time())
    claims = {
        "iss": iss,
        "aud": aud,
        "exp": now + exp_offset,
        "nbf": now + nbf_offset,
        "iat": now,
        "serviceUrl": service_url,
    }
    h_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    c_b64 = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{h_b64}.{c_b64}".encode("ascii")
    sig = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{h_b64}.{c_b64}.{_b64url(sig)}"


@pytest.fixture(scope="module")
def keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str]:
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return priv, priv.public_key(), "test-kid-1"


def test_verify_accepts_valid_token(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, kid = keypair
    token = _mint_jwt(private_key=priv, kid=kid, aud="bot-app-id")
    claims = verify_teams_activity_jwt(
        token=token,
        expected_app_id="bot-app-id",
        expected_service_url="https://smba.trafficmanager.net/uk/",
        fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
    )
    assert claims["aud"] == "bot-app-id"
    assert claims["serviceUrl"] == "https://smba.trafficmanager.net/uk/"


def test_verify_rejects_wrong_audience(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, kid = keypair
    token = _mint_jwt(private_key=priv, kid=kid, aud="someone-elses-bot")
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_rejects_wrong_issuer(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, kid = keypair
    token = _mint_jwt(
        private_key=priv,
        kid=kid,
        aud="bot-app-id",
        iss="https://attacker.example/",
    )
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_rejects_serviceUrl_mismatch(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    """Defends against bot-id collision attacks: an attacker who
    spoofs an activity must also predict the serviceUrl."""
    priv, pub, kid = keypair
    token = _mint_jwt(
        private_key=priv,
        kid=kid,
        aud="bot-app-id",
        service_url="https://smba.trafficmanager.net/uk/",
    )
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            expected_service_url="https://different.example/",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_rejects_unknown_kid(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, _ = keypair
    token = _mint_jwt(private_key=priv, kid="not-in-jwks", aud="bot-app-id")
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(pub, "different-kid")],
        )


def test_verify_rejects_expired_token(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, kid = keypair
    token = _mint_jwt(
        private_key=priv,
        kid=kid,
        aud="bot-app-id",
        exp_offset=-3600,  # expired 1 hour ago
    )
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_rejects_token_signed_by_wrong_key(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, _pub, kid = keypair
    token = _mint_jwt(private_key=priv, kid=kid, aud="bot-app-id")
    # JWKS lists a DIFFERENT public key for the same kid → sig fails
    other_pub = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    ).public_key()
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(other_pub, kid)],
        )


def test_verify_rejects_non_rs256_alg(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    """Algorithm-substitution attack: token claims `alg=none` or
    `alg=HS256`. Must reject regardless of signature."""
    _, pub, kid = keypair
    header = {"alg": "none", "typ": "JWT", "kid": kid}
    claims = {
        "iss": EXPECTED_ISSUER,
        "aud": "bot-app-id",
        "exp": int(time.time()) + 3600,
    }
    h = _b64url(json.dumps(header).encode())
    c = _b64url(json.dumps(claims).encode())
    token = f"{h}.{c}."
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="bot-app-id",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_rejects_malformed_token(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    _, pub, kid = keypair
    for bogus in ("", "not-a-jwt", "a.b", "a.b.c.d", "....."):
        with pytest.raises(TeamsAuthError):
            verify_teams_activity_jwt(
                token=bogus,
                expected_app_id="bot-app-id",
                fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
            )


def test_verify_rejects_empty_inputs(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    priv, pub, kid = keypair
    token = _mint_jwt(private_key=priv, kid=kid, aud="bot-app-id")

    # Empty token
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token="", expected_app_id="x", fetch_jwks=lambda: []
        )
    # Empty app_id
    with pytest.raises(TeamsAuthError):
        verify_teams_activity_jwt(
            token=token,
            expected_app_id="",
            fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
        )


def test_verify_error_message_is_uniform(
    keypair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey, str],
) -> None:
    """Same defense-in-depth as Discord/Twilio verifiers: don't tell
    attackers which check failed."""
    priv, pub, kid = keypair
    msgs = []
    cases = [
        ("wrong-aud", _mint_jwt(private_key=priv, kid=kid, aud="x")),
        ("wrong-iss", _mint_jwt(private_key=priv, kid=kid, aud="bot", iss="https://attacker.example/")),
        ("wrong-key", _mint_jwt(private_key=priv, kid="other", aud="bot")),
    ]
    for _name, tok in cases:
        try:
            verify_teams_activity_jwt(
                token=tok,
                expected_app_id="bot",
                fetch_jwks=lambda: [_make_jwks_entry(pub, kid)],
            )
        except TeamsAuthError as exc:
            msgs.append(str(exc))
    assert all(m == "invalid bot token" for m in msgs), msgs
