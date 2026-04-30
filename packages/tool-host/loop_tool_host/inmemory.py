"""In-memory `Sandbox` implementation for tests and the studio.

Uses a caller-supplied async ``handler(tool, arguments)`` callable to
fake the MCP server. The studio's local-MCP shim plugs the real
in-process MCP client behind this interface so the same `WarmPool`
code path serves both unit tests and dev runs.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from loop_tool_host.errors import SandboxStartupError
from loop_tool_host.models import SandboxConfig, SandboxExecResult, SandboxState

ExecHandler = Callable[[str, dict[str, Any]], Awaitable[Any]]


class InMemorySandbox:
    """Stub `Sandbox` impl driven by an async callable.

    Intentionally not a Protocol implementer subclass -- it satisfies
    the `Sandbox` protocol structurally.
    """

    def __init__(
        self,
        config: SandboxConfig,
        handler: ExecHandler,
        *,
        fail_on_start: bool = False,
    ) -> None:
        self._config = config
        self._handler = handler
        self._state: SandboxState = SandboxState.PENDING
        self._fail_on_start = fail_on_start

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def state(self) -> SandboxState:
        return self._state

    async def start(self) -> None:
        if self._state is not SandboxState.PENDING:
            return
        if self._fail_on_start:
            raise SandboxStartupError(
                f"in-memory sandbox start failed for {self._config.mcp_server}"
            )
        self._state = SandboxState.READY

    async def exec(
        self, *, tool: str, arguments: dict[str, Any]
    ) -> SandboxExecResult:
        if self._state is not SandboxState.READY:
            return SandboxExecResult(
                ok=False, error=f"sandbox not ready: {self._state.value}"
            )
        self._state = SandboxState.RUNNING
        started = time.perf_counter()
        try:
            payload = await self._handler(tool, arguments)
        except Exception as exc:
            return SandboxExecResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        finally:
            # Pool may release-then-reuse, so back to READY not TERMINATED.
            if self._state is SandboxState.RUNNING:
                self._state = SandboxState.READY
        return SandboxExecResult(
            ok=True,
            payload=payload,
            duration_ms=(time.perf_counter() - started) * 1000,
        )

    async def shutdown(self) -> None:
        self._state = SandboxState.TERMINATED


class InMemorySandboxFactory:
    """`SandboxFactory` impl that hands out `InMemorySandbox`es."""

    def __init__(
        self,
        handler: ExecHandler,
        *,
        fail_starts: int = 0,
    ) -> None:
        self._handler = handler
        self._remaining_failures = fail_starts
        self.created: list[InMemorySandbox] = []

    async def create(self, config: SandboxConfig) -> InMemorySandbox:
        fail = self._remaining_failures > 0
        if fail:
            self._remaining_failures -= 1
        sandbox = InMemorySandbox(config, self._handler, fail_on_start=fail)
        self.created.append(sandbox)
        return sandbox


__all__ = ["ExecHandler", "InMemorySandbox", "InMemorySandboxFactory"]
