"""Runtime orchestration for MCP tool calls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from loop_tool_host.mcp_governance import ToolPolicy, ToolQuota
from loop_tool_host.sandbox import Sandbox


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ToolCall(_StrictModel):
    workspace_id: str
    agent_id: str
    tool: str
    arguments: dict[str, object] = Field(default_factory=dict)
    scopes: tuple[str, ...] = ()
    timeout_ms: int = Field(default=30_000, ge=100)


class ToolExecutionFrame(_StrictModel):
    ok: bool
    payload: object | None = None
    error_code: str | None = None
    error: str | None = None
    duration_ms: int = Field(default=0, ge=0)


class ToolExecutor:
    """Apply policy and timeout around one sandbox tool execution."""

    def __init__(
        self,
        sandbox: Sandbox,
        *,
        policy: ToolPolicy | None = None,
    ) -> None:
        self._sandbox = sandbox
        self._policy = policy or ToolPolicy()

    async def execute(self, call: ToolCall) -> ToolExecutionFrame:
        decision = self._policy.authorize(tool=call.tool, scopes=call.scopes)
        if not decision.allowed:
            return ToolExecutionFrame(
                ok=False,
                error_code=decision.code,
                error=decision.reason,
            )
        try:
            result = await asyncio.wait_for(
                self._sandbox.exec(tool=call.tool, arguments=call.arguments),
                timeout=call.timeout_ms / 1000,
            )
        except TimeoutError:
            return ToolExecutionFrame(
                ok=False,
                error_code="LOOP-TH-401",
                error="tool execution timed out",
            )
        except asyncio.CancelledError:
            await self._sandbox.shutdown()
            raise
        if not result.ok:
            return ToolExecutionFrame(
                ok=False,
                error_code="LOOP-TH-500",
                error=result.error,
                duration_ms=int(result.duration_ms),
            )
        return ToolExecutionFrame(
            ok=True,
            payload=result.payload,
            duration_ms=int(result.duration_ms),
        )


class PoolDemand(_StrictModel):
    workspace_id: str
    tool: str
    in_flight: int = Field(ge=0)
    idle: int = Field(ge=0)
    queued: int = Field(ge=0)
    min_idle: int = Field(ge=0)
    max_size: int = Field(ge=1)


class PoolReconcileAction(_StrictModel):
    action: Literal["scale-up", "scale-down", "hold"]
    target_idle: int = Field(ge=0)
    reason: str


class WarmPoolController:
    def plan(self, demand: PoolDemand) -> PoolReconcileAction:
        if demand.min_idle > demand.max_size:
            raise ValueError("min_idle cannot exceed max_size")
        if demand.queued > 0 or demand.idle < demand.min_idle:
            target_total = min(demand.max_size, demand.in_flight + demand.min_idle + demand.queued)
            target_idle = max(0, target_total - demand.in_flight)
            return PoolReconcileAction(
                action="scale-up",
                target_idle=target_idle,
                reason="queued work or idle floor breached",
            )
        if demand.queued == 0 and demand.idle > demand.min_idle:
            return PoolReconcileAction(
                action="scale-down",
                target_idle=demand.min_idle,
                reason="idle capacity above floor",
            )
        return PoolReconcileAction(action="hold", target_idle=demand.idle, reason="within bounds")


class ToolConfigVersion(_StrictModel):
    tool: str
    version: str
    config_digest: str
    quota: ToolQuota


class HotRestartPlan(_StrictModel):
    restart_required: bool
    drain_timeout_ms: int = Field(ge=0)
    old_digest: str | None = None
    new_digest: str | None = None
    reason: str


class HotRestartPlanner:
    def plan(
        self,
        *,
        old: ToolConfigVersion,
        new: ToolConfigVersion,
        in_flight_calls: int,
        drain_timeout_ms: int = 60_000,
    ) -> HotRestartPlan:
        if old.config_digest == new.config_digest:
            return HotRestartPlan(restart_required=False, reason="config unchanged")
        reason = "drain in-flight calls before staggered refresh"
        if in_flight_calls == 0:
            reason = "refresh immediately"
        return HotRestartPlan(
            restart_required=True,
            drain_timeout_ms=drain_timeout_ms,
            old_digest=old.config_digest,
            new_digest=new.config_digest,
            reason=reason,
        )


class McpProtocolNegotiationError(Exception):
    code = "LOOP-TH-601"


class McpProtocolNegotiation(_StrictModel):
    version: str
    downgraded: bool


class McpProtocolNegotiator:
    def __init__(self, supported_versions: tuple[str, ...]) -> None:
        if not supported_versions:
            raise ValueError("at least one MCP version is required")
        self._supported = tuple(sorted(supported_versions, key=_version_key, reverse=True))

    def negotiate(self, peer_versions: tuple[str, ...]) -> McpProtocolNegotiation:
        peer = set(peer_versions)
        for version in self._supported:
            if version in peer:
                return McpProtocolNegotiation(
                    version=version,
                    downgraded=version != self._supported[0],
                )
        raise McpProtocolNegotiationError("no compatible MCP protocol version")


class RuntimeToolDescriptor(_StrictModel):
    name: str
    description: str
    input_schema: dict[str, object]


class RuntimeToolHandler(Protocol):
    def invoke(self, name: str, arguments: dict[str, object]) -> Awaitable[object]: ...


class InboundMcpServer:
    """Expose Loop runtime operations as an MCP-like local server."""

    def __init__(
        self,
        descriptors: tuple[RuntimeToolDescriptor, ...],
        handler: RuntimeToolHandler,
        *,
        policy: ToolPolicy | None = None,
    ) -> None:
        names = {descriptor.name for descriptor in descriptors}
        if len(names) != len(descriptors):
            raise ValueError("duplicate runtime tool descriptor")
        self._descriptors = descriptors
        self._handler = handler
        self._policy = policy or ToolPolicy()

    def list_tools(self) -> tuple[RuntimeToolDescriptor, ...]:
        return self._descriptors

    async def call_tool(
        self,
        *,
        name: str,
        arguments: dict[str, object],
        scopes: tuple[str, ...] = (),
    ) -> ToolExecutionFrame:
        if name not in {descriptor.name for descriptor in self._descriptors}:
            return ToolExecutionFrame(
                ok=False,
                error_code="LOOP-TH-404",
                error=f"unknown runtime tool {name!r}",
            )
        decision = self._policy.authorize(tool=name, scopes=scopes)
        if not decision.allowed:
            return ToolExecutionFrame(ok=False, error_code=decision.code, error=decision.reason)
        payload = await self._handler.invoke(name, arguments)
        return ToolExecutionFrame(ok=True, payload=payload)


class ToolVersion(_StrictModel):
    tool: str
    version: str
    image_digest: str
    manifest_digest: str
    published_ms: int = Field(ge=0)


class ToolVersionRegistry:
    def __init__(self) -> None:
        self._staged: dict[tuple[str, str], ToolVersion] = {}
        self._active: dict[str, ToolVersion] = {}
        self._history: dict[str, list[ToolVersion]] = {}

    def stage(self, version: ToolVersion) -> None:
        self._staged[(version.tool, version.version)] = version

    def publish(self, *, tool: str, version: str) -> ToolVersion:
        key = (tool, version)
        if key not in self._staged:
            raise KeyError(f"tool version not staged: {tool}@{version}")
        selected = self._staged[key]
        if tool in self._active:
            self._history.setdefault(tool, []).append(self._active[tool])
        self._active[tool] = selected
        return selected

    def active(self, tool: str) -> ToolVersion:
        try:
            return self._active[tool]
        except KeyError as exc:
            raise KeyError(f"no active version for tool {tool!r}") from exc

    def rollback(self, tool: str) -> ToolVersion:
        history = self._history.get(tool, [])
        if not history:
            raise KeyError(f"no rollback version for tool {tool!r}")
        selected = history.pop()
        self._active[tool] = selected
        return selected


def _version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


ToolHandlerFunc = Callable[[str, dict[str, object]], Awaitable[object]]


__all__ = [
    "HotRestartPlan",
    "HotRestartPlanner",
    "InboundMcpServer",
    "McpProtocolNegotiation",
    "McpProtocolNegotiationError",
    "McpProtocolNegotiator",
    "PoolDemand",
    "PoolReconcileAction",
    "RuntimeToolDescriptor",
    "RuntimeToolHandler",
    "ToolCall",
    "ToolConfigVersion",
    "ToolExecutionFrame",
    "ToolExecutor",
    "ToolHandlerFunc",
    "ToolVersion",
    "ToolVersionRegistry",
    "WarmPoolController",
]
