"""Argument + result schema validation (S723).

Tools declare JSON-Schema fragments for their arguments and their
results. The tool-host validates *before* dispatch (bad args -> typed
``ToolSchemaError`` with ``LOOP-TH-002``) and *after* execution (bad
result -> same error in the result frame).

We support a deliberately narrow JSON Schema subset:

* ``type``: object|array|string|number|integer|boolean|null
* ``required`` (object only)
* ``properties`` (object only)
* ``additionalProperties`` (object only; defaults to False, locked-down)
* ``items`` (array only; one schema, applied to every element)
* ``enum`` (any type)
* ``minimum`` / ``maximum`` (number/integer)
* ``minLength`` / ``maxLength`` (string)
* ``pattern`` (string; Python regex)

Anything else in the schema is ignored. This is intentional \u2014 every
new keyword is one more place a tool author can shadow a Python type
coercion bug. We add keywords as required, with tests.
"""

from __future__ import annotations

import re
from typing import Any

from loop_tool_host.errors import ToolHostError

_SUPPORTED_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


class ToolSchemaError(ToolHostError):
    """Argument or result violated its declared JSON Schema."""

    code = "LOOP-TH-002"


def _type_check(value: Any, expected: str, path: str) -> None:
    if expected not in _SUPPORTED_TYPES:
        raise ToolSchemaError(f"{path}: schema declares unsupported type {expected!r}")
    expected_py = _SUPPORTED_TYPES[expected]
    # ``bool`` is a subclass of ``int`` -- exclude it from numeric checks.
    if expected in ("number", "integer") and isinstance(value, bool):
        raise ToolSchemaError(f"{path}: expected {expected}, got bool")
    if not isinstance(value, expected_py):
        raise ToolSchemaError(
            f"{path}: expected {expected}, got {type(value).__name__}"
        )


def validate(value: Any, schema: dict[str, Any], *, path: str = "$") -> None:
    """Validate ``value`` against ``schema``. Raise ``ToolSchemaError``."""
    if not isinstance(schema, dict):
        raise ToolSchemaError(f"{path}: schema must be a dict")

    declared_type = schema.get("type")
    if declared_type is not None:
        if isinstance(declared_type, list):
            # union of types -- accept first match
            matched = False
            errs: list[str] = []
            for t in declared_type:
                try:
                    _type_check(value, t, path)
                    matched = True
                    break
                except ToolSchemaError as exc:
                    errs.append(str(exc))
            if not matched:
                raise ToolSchemaError(f"{path}: no type in {declared_type} matched ({errs!r})")
        else:
            _type_check(value, declared_type, path)

    if "enum" in schema:
        allowed = schema["enum"]
        if value not in allowed:
            raise ToolSchemaError(f"{path}: value {value!r} not in enum {allowed!r}")

    if isinstance(value, dict) and (declared_type == "object" or "properties" in schema):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for req in required:
            if req not in value:
                raise ToolSchemaError(f"{path}: missing required property {req!r}")
        for key, sub in value.items():
            if key in properties:
                validate(sub, properties[key], path=f"{path}.{key}")
            elif schema.get("additionalProperties", False) is False:
                raise ToolSchemaError(f"{path}: unexpected property {key!r}")

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for idx, item in enumerate(value):
            validate(item, item_schema, path=f"{path}[{idx}]")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ToolSchemaError(f"{path}: length {len(value)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ToolSchemaError(f"{path}: length {len(value)} > maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ToolSchemaError(f"{path}: value does not match pattern {schema['pattern']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolSchemaError(f"{path}: value {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolSchemaError(f"{path}: value {value} > maximum {schema['maximum']}")


def validate_args(arguments: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate a tool-call ``arguments`` map. Errors are pre-dispatch."""
    if not isinstance(arguments, dict):
        raise ToolSchemaError("$: arguments must be an object")
    validate(arguments, schema, path="$args")


def validate_result(result: Any, schema: dict[str, Any]) -> None:
    """Validate a tool-call result before forwarding to the agent."""
    validate(result, schema, path="$result")


__all__ = [
    "ToolSchemaError",
    "validate",
    "validate_args",
    "validate_result",
]
