"""Process-local MCP tool registry.

The registry is the bridge between ``@tool``-decorated Python callables
and the rest of the runtime (TurnExecutor in S012, dp-tool-host in
S028). It keeps things simple on purpose:

* Names are unique per registry instance; re-registering the same name
  raises so silent shadowing never produces a wrong tool call.
* ``describe_all`` returns MCP-shaped descriptors ready to ship to an
  LLM gateway as the ``tools`` parameter.
* ``call`` enforces the JSON-Schema ``required`` set before invoking the
  underlying coroutine; richer validation lives in dp-tool-host.

A module-level default registry is provided for the common case of
"every imported ``@tool`` should be visible to this agent". Tests use
their own registry to stay isolated.
"""

from __future__ import annotations

from typing import Any

from loop_mcp.decorator import Tool


class ToolNotFoundError(KeyError):
    """Raised when a tool name is not registered."""


class DuplicateToolError(ValueError):
    """Raised when a tool name is registered twice."""


class ToolRegistry:
    """In-memory tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool_def: Tool) -> None:
        if tool_def.name in self._tools:
            raise DuplicateToolError(f"tool '{tool_def.name}' is already registered")
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe_all(self) -> list[dict[str, Any]]:
        return [self._tools[n].to_mcp_descriptor() for n in self.names()]

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool_def = self.get(name)
        required = tool_def.input_schema.get("required", [])
        missing = [k for k in required if k not in arguments]
        if missing:
            raise ValueError(f"tool '{name}' missing required arguments: {sorted(missing)}")
        return await tool_def.invoke(**arguments)

    def clear(self) -> None:
        """Test-only: drop all registered tools."""

        self._tools.clear()


_DEFAULT: ToolRegistry | None = None


def default_registry() -> ToolRegistry:
    """Return the singleton registry used by the bare ``@tool`` decorator."""

    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = ToolRegistry()
    return _DEFAULT
