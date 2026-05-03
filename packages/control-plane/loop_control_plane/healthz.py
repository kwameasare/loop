# perf-gate-trigger: see PR #160 for the kind-runner right-sizing.
"""cp-api healthz facade (S100).

The full FastAPI router lives behind the cp-api process. This module
exposes the *pure* health-payload builder so the runtime can return a
structured response without importing FastAPI in tests.

Used by the cp-api ``GET /healthz`` route handler:

    from loop_control_plane.healthz import build_healthz_payload
    payload = build_healthz_payload(version=__version__, ...)

The returned ``HealthInfo`` model is JSON-serialisable; the route
handler maps ``status='unhealthy'`` to HTTP 503 and everything else
to HTTP 200 — both with the same JSON shape so observability stays
uniform.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["DbProbe", "HealthInfo", "build_healthz_payload"]


# ``status='healthy'`` only when every probe returned True. Any
# missing probe defaults to True (we don't claim the dependency is
# unhealthy until we actually know it is).
HealthStatus = Literal["healthy", "degraded", "unhealthy"]


class HealthInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HealthStatus
    version: str = Field(min_length=1)
    commit_sha: str = Field(min_length=7, max_length=64)
    build_time: str = Field(min_length=1)
    db_ok: bool = True
    redis_ok: bool = True
    nats_ok: bool = True


# A probe returns True for healthy. Probes are async because real
# implementations issue network calls; tests pass plain ``async lambda``s.
DbProbe = Callable[[], Awaitable[bool]]


async def _probe_or_default(probe: DbProbe | None, *, default: bool = True) -> bool:
    if probe is None:
        return default
    try:
        return bool(await probe())
    except Exception:  # pragma: no cover — probe failures map to False.
        return False


async def build_healthz_payload(
    *,
    version: str,
    commit_sha: str,
    build_time: str,
    db_probe: DbProbe | None = None,
    redis_probe: DbProbe | None = None,
    nats_probe: DbProbe | None = None,
) -> HealthInfo:
    """Run all probes concurrently, return a serialisable health snapshot.

    Status mapping:
      * **unhealthy** — the database probe failed (cp-api is useless
        without Postgres).
      * **degraded** — non-critical probe (Redis / NATS) failed.
      * **healthy** — everything green.
    """
    db_ok = await _probe_or_default(db_probe)
    redis_ok = await _probe_or_default(redis_probe)
    nats_ok = await _probe_or_default(nats_probe)
    if not db_ok:
        status: HealthStatus = "unhealthy"
    elif not (redis_ok and nats_ok):
        status = "degraded"
    else:
        status = "healthy"
    return HealthInfo(
        status=status,
        version=version,
        commit_sha=commit_sha,
        build_time=build_time,
        db_ok=db_ok,
        redis_ok=redis_ok,
        nats_ok=nats_ok,
    )
