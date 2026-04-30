"""Sandbox + SandboxFactory protocols.

Implementations: ``loop_tool_host.inmemory`` (tests/studio) and a
future ``loop_tool_host.kubernetes`` (S028) that talks to the
control-plane API to create Pods backed by the ``loop-firecracker``
RuntimeClass declared in ``infra/k8s/runtime-class.yaml``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from loop_tool_host.models import SandboxConfig, SandboxExecResult, SandboxState


@runtime_checkable
class Sandbox(Protocol):
    """A single execution unit -- one Firecracker microVM in
    production, an in-process stub in tests."""

    @property
    def config(self) -> SandboxConfig: ...

    @property
    def state(self) -> SandboxState: ...

    async def start(self) -> None:
        """Boot the sandbox. Must transition state PENDING -> READY.

        May raise ``SandboxStartupError``; callers (the warm pool)
        treat any failure as fatal for *this* sandbox -- the pool
        will create a replacement.
        """

    async def exec(self, *, tool: str, arguments: dict[str, Any]) -> SandboxExecResult:
        """Run a tool call. Caller has already acquired the sandbox
        from the pool, so concurrent ``exec`` on the same sandbox is
        a programmer error and implementations may raise."""

    async def shutdown(self) -> None:
        """Tear down. Must transition state -> TERMINATED. Idempotent."""


@runtime_checkable
class SandboxFactory(Protocol):
    """Constructs sandboxes. The pool calls ``create`` lazily
    whenever it needs to grow."""

    async def create(self, config: SandboxConfig) -> Sandbox: ...


__all__ = ["Sandbox", "SandboxFactory"]
