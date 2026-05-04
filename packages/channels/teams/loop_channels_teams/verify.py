"""Microsoft Teams Bot Framework JWT verification.

Closes P0.5c from the prod-readiness audit. The Bot Framework signs
every inbound activity with an RS256 JWT issued by
``https://login.botframework.com``. The receiving service MUST verify
the ``Authorization: Bearer <jwt>`` header against the Bot Framework's
JWKS before processing — otherwise anyone can post a fabricated
activity to the public webhook URL and trigger agent runs.

See: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication

Verification recipe (per the Bot Framework auth doc):

1. Extract bearer token from `Authorization` header.
2. Pull the OpenID config at
   ``https://login.botframework.com/v1/.well-known/openidconfiguration``;
   from that, fetch the JWKS endpoint listed under ``jwks_uri``.
3. Look up the signing key by ``kid`` in the JWT header.
4. Verify RS256 signature with that public key.
5. Validate claims:
   - ``iss`` == ``https://api.botframework.com``
   - ``aud`` == operator's bot's Microsoft App ID
   - ``serviceUrl`` claim == the activity's ``serviceUrl`` (defends
     against bot-id collision attacks)
   - ``exp`` > now (with 5-minute clock skew)

Implementation
==============
* JWKS fetching is via injected `JwksFetcher` callable so tests stay
  hermetic (no network) and operators can plug in their own caching
  layer.
* Validation uses `cryptography` for RSA public key parsing + sig
  verification (already a dep in the workspace via discord).
* All verification failures map to a single `TeamsAuthError` with a
  generic "invalid bot token" message — same defense-in-depth posture
  as the discord verifier.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from typing import Any, Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.serialization import load_pem_public_key

DEFAULT_CLOCK_SKEW_SECONDS: Final[int] = 300
EXPECTED_ISSUER: Final[str] = "https://api.botframework.com"
JWKS_URL: Final[str] = (
    "https://login.botframework.com/v1/.well-known/openidconfiguration"
)


class TeamsAuthError(ValueError):
    """Raised when an inbound Teams activity fails JWT verification.

    Maps to HTTP 401. Generic message — never reveal which specific
    check failed (claim mismatch vs sig vs key-id vs expiry).
    """


JwksKey = dict[str, Any]
JwksFetcher = Callable[[], list[JwksKey]]


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _rsa_public_key_from_jwk(jwk: JwksKey) -> Any:
    """Reconstruct an RSA public key from a JWKS entry (n, e)."""
    if jwk.get("kty") != "RSA":
        raise TeamsAuthError("invalid bot token")
    try:
        n_b = _b64url_decode(jwk["n"])
        e_b = _b64url_decode(jwk["e"])
    except (KeyError, ValueError) as exc:
        raise TeamsAuthError("invalid bot token") from exc
    n = int.from_bytes(n_b, "big")
    e = int.from_bytes(e_b, "big")
    if jwk.get("x5c"):
        # When an x5c chain is provided, prefer it (matches what Microsoft
        # ships); fall back to (n, e) otherwise.
        try:
            cert_der = base64.b64decode(jwk["x5c"][0])
            from cryptography.x509 import load_der_x509_certificate

            return load_der_x509_certificate(cert_der).public_key()
        except Exception as exc:  # pragma: no cover  (defensive)
            raise TeamsAuthError("invalid bot token") from exc
    return RSAPublicNumbers(e=e, n=n).public_key()


def _split_jwt(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    """Return (header_dict, claims_dict, signing_input, signature_bytes)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TeamsAuthError("invalid bot token")
    try:
        header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
        claims = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        signature = _b64url_decode(parts[2])
    except (ValueError, UnicodeDecodeError) as exc:
        raise TeamsAuthError("invalid bot token") from exc
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    return header, claims, signing_input, signature


def verify_teams_activity_jwt(
    *,
    token: str,
    expected_app_id: str,
    expected_service_url: str | None = None,
    fetch_jwks: JwksFetcher,
    clock_skew_seconds: int = DEFAULT_CLOCK_SKEW_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """Verify a Bot Framework JWT from an inbound Teams activity.

    Returns the validated claims dict on success. Raises
    :class:`TeamsAuthError` on any failure.

    Parameters
    ----------
    token
        Raw JWT (the bare token, no "Bearer " prefix).
    expected_app_id
        Operator's Microsoft App ID. Validated against the JWT's ``aud``.
    expected_service_url
        The ``serviceUrl`` from the activity body. If provided, validates
        the JWT's ``serviceUrl`` claim matches — defends against a
        compromised JWKS being abused to spoof a different tenant.
        Pass ``None`` when only verifying the JWT in isolation (e.g.
        for /authorization-only endpoints), but production callers
        SHOULD always pass the activity's serviceUrl.
    fetch_jwks
        Callable returning the current JWKS keys list. The host service
        is responsible for caching + periodic refresh.
    clock_skew_seconds
        Tolerance for ``exp`` and ``nbf``. Default 300s.
    now
        Override for tests.
    """
    if not token or not expected_app_id or fetch_jwks is None:
        raise TeamsAuthError("invalid bot token")

    header, claims, signing_input, signature = _split_jwt(token)

    if header.get("alg") != "RS256":
        raise TeamsAuthError("invalid bot token")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise TeamsAuthError("invalid bot token")

    # Find the signing key by kid
    try:
        jwks = fetch_jwks()
    except Exception as exc:  # pragma: no cover - the fetcher is host-owned
        raise TeamsAuthError("invalid bot token") from exc
    matching = [k for k in jwks if k.get("kid") == kid]
    if not matching:
        raise TeamsAuthError("invalid bot token")
    pub_key = _rsa_public_key_from_jwk(matching[0])

    # Signature
    try:
        # PEM round-trip ensures we have a uniform interface across
        # x5c-derived (cert) and (n,e)-derived (raw RSA) keys.
        if not hasattr(pub_key, "verify"):
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                PublicFormat,
            )

            pub_key = load_pem_public_key(
                pub_key.public_bytes(
                    encoding=Encoding.PEM,
                    format=PublicFormat.SubjectPublicKeyInfo,
                )
            )
        pub_key.verify(  # type: ignore[union-attr]
            signature,
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except InvalidSignature as exc:
        raise TeamsAuthError("invalid bot token") from exc
    except Exception as exc:
        raise TeamsAuthError("invalid bot token") from exc

    # Claims
    iss = claims.get("iss")
    if iss != EXPECTED_ISSUER:
        raise TeamsAuthError("invalid bot token")
    aud = claims.get("aud")
    if aud != expected_app_id:
        raise TeamsAuthError("invalid bot token")
    if expected_service_url is not None and claims.get("serviceUrl") != expected_service_url:
        raise TeamsAuthError("invalid bot token")
    current = now if now is not None else time.time()
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or current > exp + clock_skew_seconds:
        raise TeamsAuthError("invalid bot token")
    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)) and current + clock_skew_seconds < nbf:
        raise TeamsAuthError("invalid bot token")

    return claims


__all__ = [
    "DEFAULT_CLOCK_SKEW_SECONDS",
    "EXPECTED_ISSUER",
    "JWKS_URL",
    "JwksFetcher",
    "JwksKey",
    "TeamsAuthError",
    "verify_teams_activity_jwt",
]
