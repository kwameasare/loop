from __future__ import annotations

import json
import os
import sys
import time
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeError(RuntimeError): ...


def _read_json(request: Request, timeout: float) -> dict[str, object]:
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return cast(dict[str, object], json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        raise SmokeError(f"{request.full_url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise SmokeError(f"{request.full_url} unavailable: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SmokeError(f"{request.full_url} returned invalid JSON") from exc


def _wait_for_health(base_url: str, region: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        request = Request(f"{base_url}/healthz", method="GET")  # noqa: S310
        try:
            if _read_json(request, timeout=2).get("ok") is True:
                return
            last_error = "health payload did not include ok=true"
        except SmokeError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SmokeError(f"runtime health check failed for {region}: {last_error}")


def _send_turn(base_url: str, region: str, timeout: float) -> dict[str, object]:
    payload = json.dumps(
        {
            "input": "hello from eu smoke",
            "region": region,
            "metadata": {"smoke": "eu-west-nightly"},
        }
    ).encode("utf-8")
    request = Request(  # noqa: S310
        f"{base_url}/v1/turns",
        data=payload,
        headers={"content-type": "application/json", "x-loop-region": region},
        method="POST",
    )
    return _read_json(request, timeout=timeout)


def run() -> None:
    base_url = os.environ.get("EU_SMOKE_BASE_URL", "http://127.0.0.1:18081").rstrip("/")
    region = os.environ.get("EU_SMOKE_REGION", "eu-west")
    timeout = float(os.environ.get("EU_SMOKE_TIMEOUT_SECONDS", "30"))
    if region != "eu-west":
        raise SmokeError(f"EU smoke must target eu-west, got {region!r}")
    _wait_for_health(base_url, region, timeout)
    response = _send_turn(base_url, region, timeout)
    reply = response.get("reply")
    reply_text = cast(dict[str, object], reply).get("text") if isinstance(reply, dict) else None
    received = str(response.get("received", ""))
    if reply_text != "helm-e2e-ok":
        raise SmokeError(f"turn response missing helm-e2e-ok reply: {response!r}")
    if "eu-west" not in received:
        raise SmokeError(f"turn response did not echo eu-west payload: {response!r}")
    print(f"eu_smoke: OK region={region} base_url={base_url}")


def main() -> int:
    try:
        run()
    except SmokeError as exc:
        print(f"eu_smoke: FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
