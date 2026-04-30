"""Loop tool-host: Firecracker/Kata sandbox + warm pool.

Public surface:

* `Sandbox` -- per-MCP-server execution unit (one Firecracker microVM
  in production, an in-process stub for tests).
* `SandboxFactory` -- creates new `Sandbox` instances. Real impls
  call into Kubernetes; the in-memory factory just constructs
  `InMemorySandbox` objects.
* `WarmPool` -- keeps `min_idle` ready sandboxes ahead of demand and
  caps total concurrency at `max_size`. Deterministic acquire/release
  semantics, no hidden background tasks beyond what callers asked
  for via `prewarm()`.
* `SandboxBusyError`, `SandboxStartupError` -- typed failures.

Real Kubernetes-backed implementations live in
``loop_tool_host.kubernetes`` (S028 -- Sprint 1). For Sprint 0 we
ship the abstractions, the k8s manifests under ``infra/k8s/``, and
the in-memory pool the runtime + studio use today.
"""

from loop_tool_host.errors import (
    SandboxBusyError,
    SandboxStartupError,
    ToolHostError,
)
from loop_tool_host.inmemory import InMemorySandbox, InMemorySandboxFactory
from loop_tool_host.models import (
    SandboxConfig,
    SandboxExecResult,
    SandboxState,
    WarmPoolStats,
)
from loop_tool_host.pool import WarmPool
from loop_tool_host.sandbox import Sandbox, SandboxFactory

__all__ = [
    "InMemorySandbox",
    "InMemorySandboxFactory",
    "Sandbox",
    "SandboxBusyError",
    "SandboxConfig",
    "SandboxExecResult",
    "SandboxFactory",
    "SandboxStartupError",
    "SandboxState",
    "ToolHostError",
    "WarmPool",
    "WarmPoolStats",
]
