"""FastAPI entrypoint for the dp-runtime service (S902)."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, FastAPI, Header, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from loop_runtime import TurnExecutor
from loop_runtime.healthz import build_runtime_healthz

from loop_data_plane._runtime_config import (
    build_gateway,
    package_version,
    runtime_build_time,
    runtime_commit_sha,
    runtime_version,
)
from loop_data_plane._turns import (
    RuntimeTurnRequest,
    TurnExecutionError,
    collect_turn,
    stream_turn_sse,
)


@dataclass
class RuntimeAppState:
    executor: TurnExecutor = field(default_factory=lambda: TurnExecutor(build_gateway()))


def _state(request: Request) -> RuntimeAppState:
    return request.app.state.runtime


def _wants_sse(accept: str | None, stream: bool) -> bool:
    return stream or "text/event-stream" in (accept or "")


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message},
    )


router = APIRouter(tags=["Runtime"])


@router.get("/healthz")
@router.get("/v1/healthz")
async def healthz() -> JSONResponse:
    payload = await build_runtime_healthz(
        version=runtime_version(),
        commit_sha=runtime_commit_sha(),
        build_time=runtime_build_time(),
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
        "version": runtime_version(),
        "commit_sha": runtime_commit_sha(),
        "build_time": runtime_build_time(),
    }


@router.post("/v1/turns", response_model=None)
async def post_turn(
    request: Request,
    body: RuntimeTurnRequest,
    accept: str | None = Header(default=None, alias="Accept"),
    stream: bool = Query(default=False),
) -> JSONResponse | StreamingResponse:
    executor = _state(request).executor
    if _wants_sse(accept, stream):
        return StreamingResponse(
            stream_turn_sse(executor, body),
            media_type="text/event-stream",
            headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
        )
    try:
        return JSONResponse(await collect_turn(executor, body))
    except TurnExecutionError as exc:
        return _error_response(exc.code, str(exc), 502)


@router.post("/v1/turns/stream", response_model=None)
async def post_turn_stream(
    request: Request,
    body: RuntimeTurnRequest,
) -> StreamingResponse:
    return StreamingResponse(
        stream_turn_sse(_state(request).executor, body),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


def create_app(state: RuntimeAppState | None = None) -> FastAPI:
    app = FastAPI(title="Loop Data Plane Runtime", version=package_version())
    app.state.runtime = state or RuntimeAppState()
    app.include_router(router)
    return app


app = create_app()


__all__ = ["RuntimeAppState", "app", "create_app"]
