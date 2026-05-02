# pyright: basic
"""In-process Starlette ASGI app driven by ``openapi.yaml``.

For every path declared in the spec we register a single Starlette
route with a method dispatcher. The dispatcher:

* Returns ``405 Method Not Allowed`` for HTTP methods not declared on
  the path (so schemathesis' ``unsupported_method`` check stays green).
* Returns ``401 Unauthorized`` when an operation inherits non-empty
  ``security`` and the caller did not supply ``Authorization: Bearer
  …`` (covers ``ignored_auth``).
* Returns ``400 Bad Request`` (RFC 9457 ``ProblemDetail``) when a
  required header / query / cookie parameter is missing or when the
  request body fails JSON-Schema validation against the operation's
  ``requestBody`` (covers ``missing_required_header`` and
  ``negative_data_rejection``).
* Otherwise synthesizes a 2xx response from the operation's first
  declared 2xx response — body via :mod:`tests.openapi_stub.synthesize`
  and headers from the response's ``headers:`` block.

The stub is *contract-only*: it does not persist state or run real
business logic. It exists solely to give schemathesis an ASGI target
it can hammer to verify the spec's response schemas and parameter
declarations are internally consistent.
"""

from __future__ import annotations

import json
import re
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from .synthesize import synthesize

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "loop_implementation" / "api" / "openapi.yaml"

# A single fixed bearer token recognised as "valid" by the stub. Any
# other token is rejected with 401 so schemathesis' ``ignored_auth``
# probe (which substitutes garbage credentials) gets the expected
# rejection.
VALID_BEARER_TOKEN = "test-token"

_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def _load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    assert isinstance(spec, dict), "openapi spec must be a mapping"
    return spec


def load_spec(path: Path | str = DEFAULT_SPEC_PATH) -> dict[str, Any]:
    """Public alias for :func:`_load_spec` used by the test module."""

    return _load_spec(Path(path))


def _resolve(node: Any, root: dict[str, Any]) -> Any:
    if isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        assert ref.startswith("#/"), f"only local refs supported: {ref}"
        cur: Any = root
        for part in ref[2:].split("/"):
            cur = cur[part]
        return _resolve(cur, root)
    return node


def _select_response(
    operation: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    responses: dict[str, Any] = operation.get("responses") or {}
    twoxx = sorted(
        (code for code in responses if code.startswith("2") and code != "204"),
        key=lambda c: int(c) if c.isdigit() else 999,
    )
    if twoxx:
        code = twoxx[0]
    elif "default" in responses:
        code = "default"
    else:
        code = next(iter(responses), "200")
    return (
        int(code) if code.isdigit() else 200,
        _resolve(responses.get(code, {}), spec),
    )


def _select_content(
    response: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    content: dict[str, Any] = response.get("content") or {}
    if not content:
        return (None, None)
    if "application/json" in content:
        return ("application/json", content["application/json"])
    if "text/event-stream" in content:
        return ("text/event-stream", content["text/event-stream"])
    media_type = next(iter(content))
    return (media_type, content[media_type])


def _synth_headers(
    response: dict[str, Any],
    root: dict[str, Any],
) -> dict[str, str]:
    out: dict[str, str] = {}
    headers: dict[str, Any] = response.get("headers") or {}
    for name, header in headers.items():
        header = _resolve(header, root)
        schema: dict[str, Any] = header.get("schema") or {}
        value = synthesize(schema, root)
        if value is None:
            continue
        out[name] = str(value)
    return out


def _operation_requires_auth(
    operation: dict[str, Any],
    spec: dict[str, Any],
) -> bool:
    if "security" in operation:
        return bool(operation["security"])
    return bool(spec.get("security"))


def _problem(
    status: int,
    title: str,
    detail: str | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    payload: dict[str, Any] = {
        "type": f"https://api.loop.example/errors/{status}",
        "status": status,
        "title": title,
    }
    if detail:
        payload["detail"] = detail
    return JSONResponse(payload, status_code=status, headers=headers)


def _required_params(
    operation: dict[str, Any],
    path_item: dict[str, Any],
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Resolved required parameters for an operation.

    Path-level params are merged with operation-level (operation
    overrides path on ``(name, in)`` collision per OpenAPI 3.1).
    """

    out: dict[tuple[str, str], dict[str, Any]] = {}
    raw_params: list[Any] = (path_item.get("parameters") or []) + (
        operation.get("parameters") or []
    )
    for raw in raw_params:
        param = _resolve(raw, spec)
        if param.get("required"):
            out[(param["name"], param["in"])] = param
    return list(out.values())


def _request_schema(
    operation: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    body = _resolve(operation.get("requestBody") or {}, spec)
    required = bool(body.get("required"))
    content = body.get("content") or {}
    media = content.get("application/json")
    if media:
        return required, _resolve(media.get("schema") or {}, spec)
    return required, None


def _check_required_params(
    request: Request,
    params: list[dict[str, Any]],
) -> Response | None:
    for param in params:
        loc = param["in"]
        name = param["name"]
        if loc == "path":
            # Path params are validated by Starlette's routing layer.
            continue
        if loc == "query":
            if name not in request.query_params:
                return _problem(400, "Bad Request", f"missing required query '{name}'")
        elif loc == "header":
            if name.lower() == "authorization":
                # Authorization is enforced via the auth check.
                continue
            if name not in request.headers:
                return _problem(400, "Bad Request", f"missing required header '{name}'")
        elif loc == "cookie" and name not in request.cookies:
            return _problem(400, "Bad Request", f"missing required cookie '{name}'")
    return None


async def _check_request_body(
    request: Request,
    required: bool,
    schema: dict[str, Any] | None,
    spec: dict[str, Any],
) -> Response | None:
    if not schema:
        return None
    # If the spec declares multiple body content types (e.g. JSON +
    # multipart) schemathesis may pick the non-JSON one. Skip strict
    # JSON-Schema validation for those — the operation declared the
    # alternate content type as acceptable so the stub trusts it.
    content_type = request.headers.get("content-type", "").lower()
    if content_type and "application/json" not in content_type:
        return None
    raw = await request.body()
    if not raw:
        if required:
            return _problem(400, "Bad Request", "request body required")
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _problem(400, "Bad Request", "request body is not valid JSON")
    try:
        with warnings.catch_warnings():
            # ``jsonschema.RefResolver`` is deprecated in favour of the
            # newer ``referencing`` library, but the new API does not
            # transparently handle OpenAPI 3.1's ``#/components/...``
            # refs against an embedded root the way ``RefResolver``
            # does. We pin the legacy resolver here and suppress the
            # warning to keep the test output clean.
            warnings.simplefilter("ignore", DeprecationWarning)
            jsonschema.validate(
                payload,
                schema,
                resolver=jsonschema.RefResolver.from_schema(spec),
            )
    except jsonschema.ValidationError as exc:
        return _problem(400, "Bad Request", str(exc.message))
    return None


def _make_method_handler(
    operation: dict[str, Any],
    path_item: dict[str, Any],
    spec: dict[str, Any],
):  # type: ignore[no-untyped-def]
    code, response = _select_response(operation, spec)
    media_type, content = _select_content(response)
    headers = _synth_headers(response, spec)
    requires_auth = _operation_requires_auth(operation, spec)
    required_params = _required_params(operation, path_item, spec)
    body_required, body_schema = _request_schema(operation, spec)

    payload: Any = None
    sse_body: str | None = None
    if media_type == "text/event-stream":
        sse_body = (
            "data: " + json.dumps(synthesize((content or {}).get("schema") or {}, spec)) + "\n\n"
        )
    elif media_type is not None:
        payload = synthesize((content or {}).get("schema") or {}, spec)

    async def handler(request: Request) -> Response:
        if requires_auth:
            auth = request.headers.get("authorization", "")
            if not auth.lower().startswith("bearer "):
                return _problem(401, "Unauthorized")
            token = auth[7:].strip()
            if token != VALID_BEARER_TOKEN:
                return _problem(401, "Unauthorized")

        denial = _check_required_params(request, required_params)
        if denial is not None:
            return denial

        if request.method in {"POST", "PUT", "PATCH"}:
            denial = await _check_request_body(request, body_required, body_schema, spec)
            if denial is not None:
                return denial

        if media_type is None:
            return Response(status_code=code, headers=headers)
        if media_type == "text/event-stream":
            return PlainTextResponse(
                sse_body or "",
                status_code=code,
                media_type="text/event-stream",
                headers=headers,
            )
        if media_type == "application/json":
            return JSONResponse(payload, status_code=code, headers=headers)
        return Response(
            content=json.dumps(payload),
            status_code=code,
            media_type=media_type,
            headers=headers,
        )

    return handler


def _make_path_dispatcher(
    path_item: dict[str, Any],
    spec: dict[str, Any],
):  # type: ignore[no-untyped-def]
    handlers: dict[str, Any] = {}
    for method in _HTTP_METHODS:
        op = path_item.get(method)
        if isinstance(op, dict):
            handlers[method.upper()] = _make_method_handler(op, path_item, spec)

    allow = ", ".join(sorted(handlers))

    async def dispatch(request: Request) -> Response:
        handler = handlers.get(request.method)
        if handler is None:
            return _problem(
                405,
                "Method Not Allowed",
                detail=f"allowed: {allow}",
                headers={"Allow": allow},
            )
        return await handler(request)

    return dispatch, sorted(handlers.keys())


def _base_path(spec: dict[str, Any]) -> str:
    for server in spec.get("servers") or []:
        url = server.get("url", "")
        match = re.search(r"https?://[^/]+(/.*)?", url)
        if match and match.group(1):
            return match.group(1).rstrip("/")
    return ""


def server_base_path(spec: dict[str, Any]) -> str:
    """Public alias for :func:`_base_path` used by the test module."""

    return _base_path(spec)


def _iter_routes(spec: dict[str, Any]) -> Iterable[Route]:
    base = _base_path(spec)
    paths: dict[str, Any] = spec.get("paths") or {}
    for raw_path, item in paths.items():
        if not isinstance(item, dict):
            continue
        dispatch, methods = _make_path_dispatcher(item, spec)
        if not methods:
            continue
        # Register the route for *all* HTTP methods so the dispatcher
        # itself can return 405 for undocumented ones rather than
        # falling through Starlette's 404.
        yield Route(
            f"{base}{raw_path}",
            dispatch,
            methods=[m.upper() for m in _HTTP_METHODS],
        )


def build_app(spec_path: Path | str = DEFAULT_SPEC_PATH) -> Starlette:
    """Build a Starlette ASGI app from an OpenAPI spec on disk.

    The app additionally serves the spec itself at ``/openapi.json`` so
    schemathesis' ``from_asgi`` loader can fetch it in-process.
    """

    spec = _load_spec(Path(spec_path))
    routes = list(_iter_routes(spec))

    async def _serve_spec(_request: Request) -> Response:
        return JSONResponse(spec)

    routes.append(Route("/openapi.json", _serve_spec, methods=["GET"]))
    return Starlette(debug=False, routes=routes)


def build_default_app() -> Starlette:
    """Build the app bound to the repo's canonical openapi.yaml."""

    return build_app(DEFAULT_SPEC_PATH)
