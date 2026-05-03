"""Health/version routes for the cp-api app."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from loop_control_plane._app_common import env, package_version
from loop_control_plane.healthz import build_healthz_payload

router = APIRouter(tags=["Health"])


@router.get("/healthz")
@router.get("/v1/healthz")
async def healthz() -> JSONResponse:
    payload = await build_healthz_payload(
        version=env("LOOP_CP_VERSION", package_version()),
        commit_sha=env("LOOP_CP_COMMIT_SHA", "0000000-local"),
        build_time=env("LOOP_CP_BUILD_TIME", datetime.now(UTC).isoformat()),
    )
    body = payload.model_dump(mode="json")
    body["ok"] = payload.status != "unhealthy"
    code = status.HTTP_503_SERVICE_UNAVAILABLE if payload.status == "unhealthy" else 200
    return JSONResponse(status_code=code, content=body)


@router.get("/readyz")
@router.get("/v1/readyz")
async def readyz() -> dict[str, bool]:
    return {"ok": True}


@router.get("/version")
@router.get("/v1/version")
async def version_route() -> dict[str, str]:
    return {
        "version": env("LOOP_CP_VERSION", package_version()),
        "commit_sha": env("LOOP_CP_COMMIT_SHA", "0000000-local"),
        "build_time": env("LOOP_CP_BUILD_TIME", datetime.now(UTC).isoformat()),
    }
