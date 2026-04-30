"""ApiKey bearer-auth middleware adapter (S116).

Sits in front of the cp-api FastAPI app: extracts ``Authorization:
Bearer loop_sk_*`` from request headers, validates the secret against
:class:`ApiKeyService` (which already hashes + compares constant-time)
and produces an :class:`ApiKeyPrincipal` the route handlers consume
via dependency injection.

The middleware itself is framework-agnostic — it returns an
:class:`AuthDecision` that the FastAPI shim translates into a 401
response or a request-scoped principal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from loop_control_plane.api_keys import KEY_PREFIX, ApiKeyError, ApiKeyService

__all__ = [
    "ApiKeyMiddleware",
    "ApiKeyPrincipal",
    "AuthDecision",
    "extract_bearer",
]

_BEARER_PREFIX: Final = "Bearer "


@dataclass(frozen=True)
class ApiKeyPrincipal:
    api_key_id: UUID
    workspace_id: UUID


@dataclass(frozen=True)
class AuthDecision:
    principal: ApiKeyPrincipal | None
    error_code: str | None
    error_message: str | None

    @property
    def authorised(self) -> bool:
        return self.principal is not None


def extract_bearer(authorization_header: str | None) -> str | None:
    """Pull the bearer value out of an Authorization header.

    Returns ``None`` on missing / unsupported scheme rather than
    raising — the caller decides whether to 401 or fall through.
    """
    if not authorization_header:
        return None
    if not authorization_header.startswith(_BEARER_PREFIX):
        return None
    value = authorization_header[len(_BEARER_PREFIX) :].strip()
    return value or None


class ApiKeyMiddleware:
    """Authenticate a request via a workspace API key.

    Constructor takes the existing :class:`ApiKeyService` so we share
    the same hashing + constant-time compare path the issuance flow
    uses. Errors are returned as structured codes:

    * ``LOOP-AUTH-100`` — missing Authorization header
    * ``LOOP-AUTH-101`` — unsupported auth scheme / not a workspace key
    * ``LOOP-AUTH-102`` — key is unknown / revoked / mac mismatch
    """

    def __init__(self, service: ApiKeyService) -> None:
        self._service = service

    async def authenticate(
        self, authorization_header: str | None
    ) -> AuthDecision:
        if not authorization_header:
            return AuthDecision(
                principal=None,
                error_code="LOOP-AUTH-100",
                error_message="missing Authorization header",
            )
        if not authorization_header.startswith(_BEARER_PREFIX):
            return AuthDecision(
                principal=None,
                error_code="LOOP-AUTH-101",
                error_message="unsupported auth scheme",
            )
        plaintext = authorization_header[len(_BEARER_PREFIX) :].strip()
        if not plaintext.startswith(KEY_PREFIX):
            return AuthDecision(
                principal=None,
                error_code="LOOP-AUTH-101",
                error_message="bearer token is not a workspace API key",
            )
        try:
            record = await self._service.verify(plaintext)
        except ApiKeyError as exc:
            return AuthDecision(
                principal=None,
                error_code="LOOP-AUTH-102",
                error_message=str(exc),
            )
        return AuthDecision(
            principal=ApiKeyPrincipal(
                api_key_id=record.id,
                workspace_id=record.workspace_id,
            ),
            error_code=None,
            error_message=None,
        )
