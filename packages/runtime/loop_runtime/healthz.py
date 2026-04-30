"""dp-runtime ``/healthz`` payload (S130).

Sibling to ``loop_control_plane.healthz`` — the dp-runtime probe set
is narrower (it only depends on the database, the cp-api egress, and
its OTEL exporter). This module produces the JSON shape the route
handler returns.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["RuntimeHealth", "build_runtime_healthz"]


HealthStatus = Literal["healthy", "degraded", "unhealthy"]


class RuntimeHealth(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HealthStatus
    version: str = Field(min_length=1)
    commit_sha: str = Field(min_length=7, max_length=64)
    build_time: str = Field(min_length=1)
    db_ok: bool = True
    cp_api_ok: bool = True
    otel_ok: bool = True


Probe = Callable[[], Awaitable[bool]]


async def _safe_probe(probe: Probe | None) -> bool:
    if probe is None:
        return True
    try:
        return bool(await probe())
    except Exception:  # pragma: no cover
        return False


async def build_runtime_healthz(
    *,
    version: str,
    commit_sha: str,
    build_time: str,
    db_probe: Probe | None = None,
    cp_api_probe: Probe | None = None,
    otel_probe: Probe | None = None,
) -> RuntimeHealth:
    """DB failure → unhealthy; non-critical probe failure → degraded."""
    db_ok = await _safe_probe(db_probe)
    cp_ok = await _safe_probe(cp_api_probe)
    otel_ok = await _safe_probe(otel_probe)
    if not db_ok:
        status: HealthStatus = "unhealthy"
    elif not (cp_ok and otel_ok):
        status = "degraded"
    else:
        status = "healthy"
    return RuntimeHealth(
        status=status,
        version=version,
        commit_sha=commit_sha,
        build_time=build_time,
        db_ok=db_ok,
        cp_api_ok=cp_ok,
        otel_ok=otel_ok,
    )
