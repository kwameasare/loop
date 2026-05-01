"""Schemathesis round-trip coverage for the committed OpenAPI document."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import schemathesis
import yaml
from hypothesis import HealthCheck, settings
from schemathesis.checks import CHECKS, load_all_checks
from schemathesis.config import SchemathesisConfig
from schemathesis.generation.case import Case

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = ROOT / "loop_implementation" / "api" / "openapi.yaml"
VALID_AUTH = "Bearer loop-test-token"
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

OPENAPI_TEXT = OPENAPI_PATH.read_text(encoding="utf-8")
OPENAPI = yaml.safe_load(OPENAPI_TEXT)
load_all_checks()
ALL_CHECKS = CHECKS.get_all()

Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
Operation = dict[str, Any]
Route = tuple[re.Pattern[str], str, Operation]


def _resolve(node: Any) -> Any:
    if not isinstance(node, dict) or "$ref" not in node:
        return node
    current: Any = OPENAPI
    for part in node["$ref"].removeprefix("#/").split("/"):
        current = current[part]
    return _resolve(current)


def _example_for(schema: dict[str, Any] | None) -> Any:
    schema = _resolve(schema or {})
    if "example" in schema:
        return schema["example"]
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "allOf" in schema:
        merged: dict[str, Any] = {}
        for item in schema["allOf"]:
            value = _example_for(item)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    if "oneOf" in schema or "anyOf" in schema:
        return _example_for((schema.get("oneOf") or schema["anyOf"])[0])

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if item != "null"), "null")
    if schema_type is None and "properties" in schema:
        schema_type = "object"

    if schema_type == "object":
        properties = schema.get("properties", {})
        return {name: _example_for(properties.get(name)) for name in schema.get("required", [])}
    if schema_type == "array":
        min_items = int(schema.get("minItems", 0))
        return [_example_for(schema.get("items", {})) for _ in range(min_items)]
    if schema_type == "integer":
        return int(schema.get("minimum", 0))
    if schema_type == "number":
        return float(schema.get("minimum", 0.0))
    if schema_type == "boolean":
        return False
    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "uuid":
            return "00000000-0000-4000-8000-000000000001"
        if fmt == "date-time":
            return "2026-05-01T00:00:00Z"
        if fmt == "date":
            return "2026-05-01"
        if fmt == "uri":
            return "https://api.loop.example/resource"
        if fmt == "email":
            return "builder@loop.example"
        if "pattern" in schema and "a-z0-9-" in str(schema["pattern"]):
            return "loop-test"
        return "loop-test"
    return None


def _response_for(operation: Operation) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    responses = operation["responses"]
    status = next(
        (code for code in ("200", "201", "202", "204") if code in responses),
        next(code for code in responses if code.startswith("2")),
    )
    response = _resolve(responses[status])
    headers: list[tuple[bytes, bytes]] = [(b"x-loop-contract-test", b"schemathesis")]
    if status == "204" or "content" not in response:
        return int(status), headers, b""

    media_type, media = next(iter(response["content"].items()))
    headers.append((b"content-type", media_type.encode()))
    body = json.dumps(_example_for(media.get("schema"))).encode()
    return int(status), headers, body


def _compile_routes() -> list[Route]:
    routes: list[Route] = []
    for path_template, item in OPENAPI["paths"].items():
        template = f"/v1{path_template}"
        pattern = "^" + re.sub(r"\{[^/]+\}", r"[^/]+", template) + "$"
        for method, operation in item.items():
            if method in HTTP_METHODS:
                routes.append((re.compile(pattern), method.upper(), operation))
    return routes


ROUTES = _compile_routes()


def _is_public(operation: Operation) -> bool:
    return operation.get("security") == []


def _problem(status: int, title: str) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    return (
        status,
        [(b"content-type", b"application/json")],
        json.dumps({"type": "about:blank", "status": status, "title": title}).encode(),
    )


def _handle(
    method: str, path: str, headers: dict[str, str]
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    if path == "/openapi.yaml" and method == "GET":
        return 200, [(b"content-type", b"application/yaml")], OPENAPI_TEXT.encode()

    matched_methods: list[str] = []
    for pattern, route_method, operation in ROUTES:
        if not pattern.fullmatch(path):
            continue
        matched_methods.append(route_method)
        if method != route_method:
            continue
        if not _is_public(operation) and headers.get("authorization") != VALID_AUTH:
            return _problem(401, "Unauthorized")
        return _response_for(operation)

    if matched_methods:
        return 405, [(b"allow", ", ".join(sorted(matched_methods)).encode())], b""
    return _problem(404, "Not Found")


async def contract_app(scope: Message, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    if scope["type"] != "http":
        return
    headers = {
        key.decode("latin1").lower(): value.decode("latin1")
        for key, value in scope.get("headers", [])
    }
    status, response_headers, body = _handle(scope["method"], scope["path"], headers)
    await send({"type": "http.response.start", "status": status, "headers": response_headers})
    await send({"type": "http.response.body", "body": body})


CONFIG = SchemathesisConfig.from_dict(
    {
        "checks": {"enabled": True},
        "generation": {
            "mode": "positive",
            "max-examples": 1,
            "deterministic": True,
            "allow-extra-parameters": False,
            "with-security-parameters": False,
        },
        "phases": {
            "examples": {"enabled": False},
            "coverage": {"enabled": False},
            "fuzzing": {"enabled": True},
            "stateful": {"enabled": False},
        },
    }
)
SCHEMA = schemathesis.openapi.from_asgi("/openapi.yaml", contract_app, config=CONFIG)


@SCHEMA.parametrize()
@settings(
    deadline=5000,
    max_examples=1,
    database=None,
    suppress_health_check=(HealthCheck.too_slow,),
)
def test_openapi_yaml_round_trips_through_in_process_app(case: Case) -> None:
    case.call_and_validate(headers={"Authorization": VALID_AUTH}, checks=ALL_CHECKS)


def _call_app(method: str, path: str, headers: list[tuple[bytes, bytes]] | None = None) -> Message:
    messages: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Message = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(contract_app(scope, receive, send))
    return messages[0]


def test_contract_app_rejects_missing_bearer_token() -> None:
    response = _call_app("GET", "/v1/workspaces")
    assert response["status"] == 401


def test_contract_app_returns_405_with_allow_header_for_unsupported_method() -> None:
    response = _call_app(
        "PATCH",
        "/v1/workspaces",
        headers=[(b"authorization", VALID_AUTH.encode())],
    )
    assert response["status"] == 405
    assert (b"allow", b"GET") in response["headers"]
