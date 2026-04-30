"""Type-hint -> JSON Schema for MCP tool inputs.

Supports the subset that's relevant for Sprint-0 tooling:

* Primitives: str, int, float, bool, bytes (base64-encoded string).
* ``list[T]``, ``dict[str, T]``, ``T | None`` (treated as optional).
* ``Literal[...]`` (rendered as an enum).
* Pydantic models (delegated to ``model_json_schema``).
* Default values become ``default`` in the schema and remove the
  parameter from ``required``.

Anything more exotic raises :class:`UnsupportedAnnotationError` so the
agent author hears about it at decoration time, not at first tool-call.
"""

from __future__ import annotations

import inspect
import types
import typing
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel


class UnsupportedAnnotationError(TypeError):
    """Raised when a parameter annotation cannot be expressed in JSON Schema."""


_PRIMITIVE_TO_SCHEMA: dict[type, dict[str, Any]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    bytes: {"type": "string", "contentEncoding": "base64"},
}


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty:
        raise UnsupportedAnnotationError("MCP tool parameters require type hints")

    origin = get_origin(annotation)

    # Optional[T] / T | None
    if origin in (typing.Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _annotation_to_schema(args[0])
        return {"anyOf": [_annotation_to_schema(a) for a in args]}

    if origin is Literal:
        values = list(get_args(annotation))
        kinds = {type(v) for v in values}
        if kinds <= {str}:
            return {"type": "string", "enum": values}
        if kinds <= {int, bool}:
            return {"type": "integer", "enum": values}
        return {"enum": values}

    if origin in (list, tuple):
        (item_t,) = get_args(annotation) or (Any,)
        return {"type": "array", "items": _annotation_to_schema(item_t)}

    if origin is dict:
        args = get_args(annotation)
        value_t = args[1] if len(args) == 2 else Any
        return {
            "type": "object",
            "additionalProperties": _annotation_to_schema(value_t),
        }

    if annotation is Any:
        return {}

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation.model_json_schema()

    if isinstance(annotation, type) and annotation in _PRIMITIVE_TO_SCHEMA:
        return dict(_PRIMITIVE_TO_SCHEMA[annotation])

    raise UnsupportedAnnotationError(f"unsupported annotation for MCP tool: {annotation!r}")


def build_input_schema(fn: typing.Callable[..., Any]) -> dict[str, Any]:
    """Return a JSON Schema object describing ``fn``'s keyword arguments.

    Positional-only parameters are rejected -- MCP tool calls are JSON
    objects keyed by name, so every parameter must be addressable that way.
    ``self``/``cls`` are skipped if present.
    """

    signature = inspect.signature(fn)
    type_hints = typing.get_type_hints(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in signature.parameters.items():
        if name in {"self", "cls"}:
            continue
        if param.kind is inspect.Parameter.POSITIONAL_ONLY:
            raise UnsupportedAnnotationError(
                f"positional-only parameter '{name}' cannot be exposed via MCP"
            )
        if param.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise UnsupportedAnnotationError(
                f"variadic parameter '{name}' cannot be exposed via MCP"
            )

        annotation = type_hints.get(name, param.annotation)
        schema = _annotation_to_schema(annotation)
        if param.default is not inspect.Parameter.empty:
            schema = {**schema, "default": param.default}
        else:
            required.append(name)
        properties[name] = schema

    payload: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        payload["required"] = required
    return payload
