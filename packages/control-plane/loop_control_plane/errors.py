"""Map domain exceptions to canonical LOOP-API error envelopes (S118).

Every cp-api response that is not a 2xx must carry a JSON body shaped
like::

    {
        "code": "LOOP-API-101",
        "message": "Token expired",
        "request_id": "<echo of X-Request-Id>"
    }

This module turns every well-known domain exception into that envelope
so HTTP routers do not have to reinvent the mapping.

Authoritative source for the code list is
``loop_implementation/engineering/ERROR_CODES.md``; tests in this
package keep the two in sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from loop_control_plane.api_keys import ApiKeyError
from loop_control_plane.auth import AuthError
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.workspaces import WorkspaceError


@dataclass(frozen=True, slots=True)
class LoopApiError:
    """Wire-shape of a non-2xx response body."""

    code: str
    message: str
    status: int
    request_id: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "code": self.code,
            "message": self.message,
            "status": self.status,
            "request_id": self.request_id,
        }


# Canonical codes (subset relevant to cp-api S2). Full taxonomy lives in
# ``loop_implementation/engineering/ERROR_CODES.md``. Status values come
# from that doc verbatim; we re-export them so callers do not import
# the markdown.
CODE_VALIDATION = ("LOOP-API-001", 400)
CODE_TOKEN_INVALID = ("LOOP-API-101", 401)
CODE_FORBIDDEN = ("LOOP-API-102", 403)
CODE_NOT_FOUND = ("LOOP-API-201", 404)
CODE_RATE_LIMITED_PER_KEY = ("LOOP-API-302", 429)
CODE_INTERNAL = ("LOOP-API-501", 500)


def map_to_loop_api_error(exc: BaseException, *, request_id: str) -> LoopApiError:
    """Map a domain exception to a :class:`LoopApiError` envelope.

    Mapping rules:

    * :class:`AuthError` -> ``LOOP-API-101`` (token-shaped failures).
    * :class:`AuthorisationError` -> ``LOOP-API-102`` (member / role).
    * :class:`WorkspaceError` -> 404 if the message starts with
      ``"unknown "`` (matches the convention used in
      ``WorkspaceService.get`` / ``role_of``); 400 otherwise (slug
      collisions, last-owner protection, validation).
    * :class:`ApiKeyError` -> 404 if the message says ``unknown ``;
      401 if the key was rejected outright; 400 otherwise.
    * Anything else -> 500 ``LOOP-API-501``. Callers are responsible
      for redacting the message in production -- we keep ``str(exc)``
      here so dev/test traces stay readable.
    """
    code: str
    status: int
    message = str(exc) or exc.__class__.__name__

    if isinstance(exc, AuthError):
        code, status = CODE_TOKEN_INVALID
    elif isinstance(exc, AuthorisationError):
        code, status = CODE_FORBIDDEN
    elif isinstance(exc, WorkspaceError):
        if message.lower().startswith("unknown "):
            code, status = CODE_NOT_FOUND
        else:
            code, status = CODE_VALIDATION
    elif isinstance(exc, ApiKeyError):
        if message.lower().startswith("unknown "):
            code, status = CODE_NOT_FOUND
        elif message in {"key revoked", "bad secret", "invalid key format"}:
            code, status = CODE_TOKEN_INVALID
        else:
            code, status = CODE_VALIDATION
    else:
        code, status = CODE_INTERNAL

    return LoopApiError(
        code=code,
        message=message,
        status=status,
        request_id=request_id,
    )


__all__ = [
    "CODE_FORBIDDEN",
    "CODE_INTERNAL",
    "CODE_NOT_FOUND",
    "CODE_RATE_LIMITED_PER_KEY",
    "CODE_TOKEN_INVALID",
    "CODE_VALIDATION",
    "LoopApiError",
    "map_to_loop_api_error",
]
