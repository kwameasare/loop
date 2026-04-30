"""Strict pydantic v2 models for tool-host config and observability."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SandboxState(StrEnum):
    """Lifecycle states a sandbox transitions through."""

    PENDING = "pending"  # created, not yet started
    READY = "ready"  # idle, waiting for work
    RUNNING = "running"  # executing a tool call
    TERMINATED = "terminated"  # released / shut down


class SandboxConfig(_StrictModel):
    """Description of the sandbox a caller wants.

    The image digest pins the MCP server tarball; the workspace_id
    isolates pool buckets so two tenants never share a microVM
    (ADR-026).
    """

    workspace_id: str
    mcp_server: str  # logical name, e.g. "stripe", "github-mcp"
    image_digest: str  # sha256:<...>
    cpu_millis: int = Field(default=500, ge=50, le=8000)
    memory_mb: int = Field(default=256, ge=64, le=8192)
    egress_allowlist: tuple[str, ...] = ()


class SandboxExecResult(_StrictModel):
    """Result of a single ``Sandbox.exec()`` call."""

    ok: bool
    payload: Any = None
    error: str | None = None
    duration_ms: float = Field(default=0.0, ge=0.0)


class WarmPoolStats(_StrictModel):
    """Snapshot of pool occupancy. Emitted as OTel attributes by
    callers. ``in_flight`` + ``idle`` <= ``max_size`` always."""

    in_flight: int = Field(ge=0)
    idle: int = Field(ge=0)
    max_size: int = Field(ge=1)
    min_idle: int = Field(ge=0)


__all__ = [
    "SandboxConfig",
    "SandboxExecResult",
    "SandboxState",
    "WarmPoolStats",
]
