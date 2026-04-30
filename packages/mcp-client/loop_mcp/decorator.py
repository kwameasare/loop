"""``@tool`` decorator and ``Tool`` descriptor.

The decorator captures three pieces of metadata about a Python function:

* its MCP-facing name (defaults to ``fn.__name__``),
* a description (the first paragraph of its docstring),
* a JSON-Schema input contract derived from its type hints.

Decorated functions stay callable as normal Python; the descriptor lives
on ``fn.__mcp_tool__`` and is also auto-registered with the module-level
:func:`default_registry` so an agent can discover all tools imported in
its process via ``default_registry().describe_all()``.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, overload

from loop_mcp.schema import build_input_schema


@dataclass(frozen=True, slots=True)
class Tool:
    """In-process MCP tool descriptor.

    ``invoke`` is async even when the wrapped function is sync; sync
    callables are wrapped so the tool dispatcher (S012) can ``await``
    every call uniformly.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    invoke: Callable[..., Awaitable[Any]]

    def to_mcp_descriptor(self) -> dict[str, Any]:
        """Render the descriptor as an MCP ``tools/list`` entry."""

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def _extract_description(fn: Callable[..., Any]) -> str:
    doc = inspect.getdoc(fn) or ""
    # First paragraph -- the LLM-facing summary.
    head, _, _ = doc.partition("\n\n")
    return head.strip()


def _ensure_async(fn: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    if inspect.iscoroutinefunction(fn):
        return fn

    async def _wrapper(**kwargs: Any) -> Any:
        return fn(**kwargs)

    _wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
    return _wrapper


@overload
def tool(fn: Callable[..., Any]) -> Callable[..., Any]: ...
@overload
def tool(
    *, name: str | None = ..., description: str | None = ...
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
def tool(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Any:
    """Mark ``fn`` as an MCP tool.

    May be used as ``@tool`` or ``@tool(name=..., description=...)``.
    Always returns the original function (callable as before) with
    ``__mcp_tool__`` attached.
    """

    def _decorate(target: Callable[..., Any]) -> Callable[..., Any]:
        descriptor = Tool(
            name=name or target.__name__,
            description=description or _extract_description(target),
            input_schema=build_input_schema(target),
            invoke=_ensure_async(target),
        )
        target.__mcp_tool__ = descriptor  # type: ignore[attr-defined]
        # Lazy import to avoid a registry <-> decorator import cycle.
        from loop_mcp.registry import default_registry

        default_registry().register(descriptor)
        return target

    if fn is not None:
        return _decorate(fn)
    return _decorate
