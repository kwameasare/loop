"""Tool-registry initialiser from agent_version.config_json (S136).

When a turn starts the runtime resolves which tools the agent_version
declares, instantiates each via a registered factory, and returns a
``ToolRegistryLike`` consumable by the ``TurnExecutor``.

The factory map is populated at module-load time. Agent config_json shape::

    {
        "tools": [
            {"name": "search", "config": {"top_k": 5}},
            {"name": "lookup_user"},
        ]
    }

Unknown tool names raise ``ToolRegistryInitError`` so misconfiguration is
loud rather than silent.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ToolFactory",
    "ToolRegistryInitError",
    "build_registry",
]


# A factory takes the per-instance config dict and returns the tool
# implementation (a callable invoked by the executor). Async factories are
# also accepted to support warm-up I/O.
ToolImpl = Callable[..., Awaitable[Any]]
ToolFactory = Callable[[Mapping[str, Any]], ToolImpl | Awaitable[ToolImpl]]


class ToolRegistryInitError(ValueError):
    """Raised on unknown tool name, malformed config, or factory failure."""


@dataclass
class _BuiltRegistry:
    _tools: dict[str, ToolImpl] = field(default_factory=dict)

    def get(self, name: str) -> ToolImpl | None:
        return self._tools.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def __contains__(self, name: object) -> bool:
        return name in self._tools


async def build_registry(
    config_json: Mapping[str, Any],
    *,
    factories: Mapping[str, ToolFactory],
) -> _BuiltRegistry:
    """Instantiate each tool declared in ``config_json["tools"]``.

    Args:
        config_json: the agent_version.config_json value.
        factories: name -> factory map. Pass an empty map to disable tools.

    Returns:
        A ToolRegistryLike-shaped registry the TurnExecutor can use.
    """

    raw_tools = config_json.get("tools", [])
    if not isinstance(raw_tools, list):
        raise ToolRegistryInitError("config_json.tools must be a list")

    registry = _BuiltRegistry()
    for entry in raw_tools:
        if not isinstance(entry, dict):
            raise ToolRegistryInitError("each tool entry must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ToolRegistryInitError("tool entry missing 'name'")
        if name in registry:
            raise ToolRegistryInitError(f"duplicate tool name: {name}")
        factory = factories.get(name)
        if factory is None:
            raise ToolRegistryInitError(f"unknown tool: {name}")
        cfg = entry.get("config", {}) or {}
        if not isinstance(cfg, dict):
            raise ToolRegistryInitError(f"tool {name!r} config must be an object")
        try:
            built = factory(cfg)
            if hasattr(built, "__await__"):
                built = await built  # type: ignore[assignment, misc]
        except ToolRegistryInitError:
            raise
        except Exception as exc:
            raise ToolRegistryInitError(
                f"factory for {name!r} failed: {exc}"
            ) from exc
        registry._tools[name] = built  # type: ignore[assignment]
    return registry
