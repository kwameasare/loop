"""S181: published demo web-channel smoke test.

Posts a visitor question to the demo site's chat endpoint and asserts
that the response contains the configured golden answer fragment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_QUESTION = "What is Loop?"


class SmokeError(AssertionError):
    """Raised when the published demo does not meet the smoke contract."""


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def _chat_endpoint(base_url: str, override: str | None) -> str:
    if override:
        return override
    return urljoin(base_url.rstrip("/") + "/", "api/chat")


def _validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SmokeError(f"demo endpoint must be http(s): {url!r}")


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        found: list[str] = []
        for item in mapping.values():
            found.extend(_strings(item))
        return found
    if isinstance(value, list):
        found = []
        for item in cast(list[object], value):
            found.extend(_strings(item))
        return found
    return []


def _response_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    strings = _strings(parsed)
    return "\n".join(strings) if strings else text


def run_smoke(
    *,
    base_url: str,
    expected_answer: str,
    question: str = DEFAULT_QUESTION,
    endpoint: str | None = None,
    token: str | None = None,
    timeout: float = 20.0,
) -> str:
    url = _chat_endpoint(base_url, endpoint)
    _validate_http_url(url)
    headers = {"accept": "application/json", "content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    payload = json.dumps({"message": question}).encode("utf-8")
    request = Request(url, data=payload, headers=headers, method="POST")  # noqa: S310

    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = response.status
            body = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"demo returned HTTP {exc.code}: {body[:240]}") from exc
    except URLError as exc:
        raise SmokeError(f"demo request failed: {exc.reason}") from exc

    if status < 200 or status >= 300:
        raise SmokeError(f"demo returned HTTP {status}")

    text = _response_text(body)
    if expected_answer.casefold() not in text.casefold():
        raise SmokeError(
            "demo answer mismatch: "
            f"expected fragment {expected_answer!r}; response was {text[:240]!r}"
        )
    return f"e2e_web_smoke: OK endpoint={url} question={question!r}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=_env("LOOP_DEMO_URL"))
    parser.add_argument("--endpoint", default=_env("LOOP_DEMO_CHAT_ENDPOINT"))
    parser.add_argument("--question", default=_env("LOOP_DEMO_QUESTION") or DEFAULT_QUESTION)
    parser.add_argument("--expected-answer", default=_env("LOOP_DEMO_EXPECTED_ANSWER"))
    parser.add_argument("--token", default=_env("LOOP_DEMO_TOKEN"))
    parser.add_argument(
        "--timeout", type=float, default=float(_env("LOOP_DEMO_TIMEOUT_SECONDS") or 20)
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.url:
        sys.stderr.write("e2e_web_smoke: FAIL LOOP_DEMO_URL is required\n")
        return 1
    if not args.expected_answer:
        sys.stderr.write("e2e_web_smoke: FAIL LOOP_DEMO_EXPECTED_ANSWER is required\n")
        return 1
    try:
        print(
            run_smoke(
                base_url=args.url,
                endpoint=args.endpoint,
                expected_answer=args.expected_answer,
                question=args.question,
                timeout=args.timeout,
                token=args.token,
            )
        )
    except SmokeError as exc:
        sys.stderr.write(f"e2e_web_smoke: FAIL {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
