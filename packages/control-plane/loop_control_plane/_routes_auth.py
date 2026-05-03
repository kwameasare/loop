"""Auth exchange route for the cp-api app."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from loop_control_plane._app_common import env, now_ms, paseto_key
from loop_control_plane.auth import HS256Verifier
from loop_control_plane.auth_exchange import AuthExchange
from loop_control_plane.jwks import JwtClaims

router = APIRouter(tags=["Auth"])


class AuthExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(min_length=1)


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
