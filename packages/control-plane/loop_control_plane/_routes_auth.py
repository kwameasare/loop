"""Auth exchange + refresh routes for the cp-api app."""

from __future__ import annotations

import secrets
import uuid
from hashlib import sha256

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import env, now_ms, paseto_key
from loop_control_plane.auth import HS256Verifier
from loop_control_plane.auth_exchange import AuthExchange
from loop_control_plane.jwks import JwtClaims
from loop_control_plane.paseto import encode_local

router = APIRouter(tags=["Auth"])


class AuthExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(min_length=1)


class AuthRefreshRequest(BaseModel):
    """Body for POST /v1/auth/refresh."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32)


@router.post("/v1/auth/exchange")
async def auth_exchange(request: Request, body: AuthExchangeRequest) -> dict[str, object]:
    runtime = request.app.state.cp
    issuer = env("LOOP_CP_AUTH_ISSUER", "https://loop.local/")
    audience = env("LOOP_CP_AUTH_AUDIENCE", "loop-cp")
    claims = HS256Verifier(
        secret=env("LOOP_CP_LOCAL_JWT_SECRET", ""),
        issuer=issuer,
        audience=audience,
    ).verify(body.id_token)

    async def mapper(sub: str) -> str | None:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"loop:idp:{sub}"))

    exchange = AuthExchange(
        paseto_key=paseto_key(),
        refresh_store=runtime.refresh_store,
        user_mapper=mapper,
        expected_audience=audience,
    )
    jwt_claims = JwtClaims(
        sub=claims.sub,
        iss=claims.iss,
        aud=(claims.aud,),
        exp_ms=claims.exp * 1000,
        iat_ms=claims.iat * 1000,
        raw=claims.model_dump(mode="json"),
    )
    result = await exchange.exchange(claims=jwt_claims, now_ms=now_ms())
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "token_type": "Bearer",
        "access_expires_at_ms": result.access_expires_at_ms,
        "refresh_expires_at_ms": result.refresh_expires_at_ms,
    }


@router.post("/v1/auth/refresh")
async def auth_refresh(
    request: Request, body: AuthRefreshRequest
) -> dict[str, object]:
    """Exchange a refresh token for a fresh access token.

    Closes P0.4. Before this route shipped, cp issued refresh tokens
    via /v1/auth/exchange but had no endpoint to redeem them — after
    1h the access token expired and the user had to re-do the IdP
    exchange (full Auth0 redirect) every hour.

    Implements **rotation with reuse-detection**: every successful
    refresh revokes the supplied token and mints a new pair. If the
    same refresh token is presented twice (= replay or theft), the
    SECOND attempt finds nothing in the store and 401s. Production
    callers should treat any 401 from this route as a likely
    compromise and force a full re-auth on the user.
    """
    runtime = request.app.state.cp
    audience = env("LOOP_CP_AUTH_AUDIENCE", "loop-cp")

    token_hash = sha256(body.refresh_token.encode("ascii")).hexdigest()
    record = runtime.refresh_store.lookup(token_hash)
    if record is None:
        raise HTTPException(
            status_code=401, detail={"code": "LOOP-API-101", "message": "invalid refresh token"}
        )
    user_sub, expires_at_ms = record
    current_ms = now_ms()
    if expires_at_ms <= current_ms:
        # Expired — revoke and reject.
        await runtime.refresh_store.revoke(token_hash)
        raise HTTPException(
            status_code=401, detail={"code": "LOOP-API-101", "message": "invalid refresh token"}
        )

    # Rotate: revoke the supplied token and mint a fresh pair. Any
    # subsequent presentation of the OLD token will hit the
    # `record is None` branch above (reuse detection).
    await runtime.refresh_store.revoke(token_hash)

    access_ttl_ms = 60 * 60 * 1000  # 1h, matches AuthExchange default
    refresh_ttl_ms = 30 * 24 * 60 * 60 * 1000  # 30d
    new_access = encode_local(
        {"sub": user_sub, "iss": "loop", "aud": audience},
        key=paseto_key(),
        now_ms=current_ms,
        expires_in_ms=access_ttl_ms,
    )
    new_refresh = secrets.token_urlsafe(32)
    new_refresh_hash = sha256(new_refresh.encode("ascii")).hexdigest()
    new_refresh_expires_at = current_ms + refresh_ttl_ms
    await runtime.refresh_store.put(
        user_sub=user_sub,
        token_hash=new_refresh_hash,
        expires_at_ms=new_refresh_expires_at,
    )
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "Bearer",
        "access_expires_at_ms": current_ms + access_ttl_ms,
        "refresh_expires_at_ms": new_refresh_expires_at,
    }
