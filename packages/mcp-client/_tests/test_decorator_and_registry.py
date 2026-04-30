from __future__ import annotations

from typing import Literal

import pytest
from loop_mcp import Tool, build_input_schema, default_registry, tool
from loop_mcp.registry import DuplicateToolError, ToolNotFoundError, ToolRegistry
from loop_mcp.schema import UnsupportedAnnotationError
from pydantic import BaseModel


@pytest.fixture(autouse=True)
def _isolate_default_registry() -> None:
    default_registry().clear()


class _Filter(BaseModel):
    """Module-scoped pydantic model used by the schema-delegation test.

    ``typing.get_type_hints`` resolves string annotations against the
    function's globals, so models referenced from a tool signature must
    live at module scope (or be passed in via ``localns`` -- not yet
    supported).
    """

    q: str
    limit: int = 10


def test_build_schema_primitives_and_required() -> None:
    def fn(name: str, count: int = 3, *, tag: str | None = None) -> None:
        del name, count, tag

    schema = build_input_schema(fn)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["count"] == {"type": "integer", "default": 3}
    assert schema["properties"]["tag"] == {"type": "string", "default": None}
    assert schema["required"] == ["name"]


def test_build_schema_collections_and_literals() -> None:
    def fn(
        ids: list[str],
        flags: dict[str, bool],
        mode: Literal["fast", "slow"],
    ) -> None:
        del ids, flags, mode

    schema = build_input_schema(fn)
    assert schema["properties"]["ids"] == {
        "type": "array",
        "items": {"type": "string"},
    }
    assert schema["properties"]["flags"] == {
        "type": "object",
        "additionalProperties": {"type": "boolean"},
    }
    assert schema["properties"]["mode"] == {
        "type": "string",
        "enum": ["fast", "slow"],
    }


def test_build_schema_pydantic_model_delegates() -> None:
    def fn(filter: _Filter) -> None:
        del filter

    schema = build_input_schema(fn)
    assert schema["properties"]["filter"]["type"] == "object"
    assert "q" in schema["properties"]["filter"]["properties"]


def test_missing_type_hint_rejected() -> None:
    def fn(x) -> None:  # type: ignore[no-untyped-def]
        del x

    with pytest.raises(UnsupportedAnnotationError):
        build_input_schema(fn)


def test_tool_decorator_attaches_descriptor_and_registers() -> None:
    @tool
    async def lookup_order(order_id: str, fresh: bool = False) -> dict[str, str]:
        """Look up an order.

        Long form description that should not appear on the tool descriptor.
        """
        return {"order_id": order_id, "fresh": str(fresh)}

    descriptor: Tool = lookup_order.__mcp_tool__  # type: ignore[attr-defined]
    assert descriptor.name == "lookup_order"
    assert descriptor.description == "Look up an order."
    assert "order_id" in descriptor.input_schema["properties"]
    assert default_registry().names() == ["lookup_order"]


async def test_tool_decorator_wraps_sync_callables() -> None:
    @tool(name="add", description="Add two numbers.")
    def _add(a: int, b: int) -> int:
        return a + b

    descriptor: Tool = _add.__mcp_tool__  # type: ignore[attr-defined]
    result = await descriptor.invoke(a=2, b=3)
    assert result == 5
    # Original function is still directly callable as plain Python.
    assert _add(1, 2) == 3


async def test_registry_call_validates_required_args() -> None:
    registry = ToolRegistry()

    @tool
    async def echo(value: str) -> str:
        return value

    registry.register(echo.__mcp_tool__)  # type: ignore[attr-defined]

    assert await registry.call("echo", {"value": "hi"}) == "hi"
    with pytest.raises(ValueError, match="missing required arguments"):
        await registry.call("echo", {})
    with pytest.raises(ToolNotFoundError):
        registry.get("nope")


def test_registry_rejects_duplicates() -> None:
    registry = ToolRegistry()

    @tool
    async def t(x: int) -> int:
        return x

    registry.register(t.__mcp_tool__)  # type: ignore[attr-defined]
    with pytest.raises(DuplicateToolError):
        registry.register(t.__mcp_tool__)  # type: ignore[attr-defined]


def test_registry_describe_all_emits_mcp_shape() -> None:
    registry = ToolRegistry()

    @tool
    async def lookup(order_id: str) -> dict[str, str]:
        """Look up an order."""
        return {"order_id": order_id}

    registry.register(lookup.__mcp_tool__)  # type: ignore[attr-defined]

    [descriptor] = registry.describe_all()
    assert descriptor["name"] == "lookup"
    assert descriptor["description"] == "Look up an order."
    assert descriptor["inputSchema"]["properties"]["order_id"] == {"type": "string"}
