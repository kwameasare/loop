"""S780: cross-cloud deploy + first-turn smoke."""

from __future__ import annotations

import argparse
import json
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
    except (HTTPError, URLError) as exc:
        raise SmokeError(f"{request.full_url} failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SmokeError(f"{request.full_url} returned invalid JSON") from exc


def _wait_for_health(base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            request = Request(f"{base_url}/healthz", method="GET")  # noqa: S310
            if _read_json(request, timeout=2).get("ok") is True:
                return
            last_error = "health payload did not include ok=true"
        except SmokeError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SmokeError(f"runtime health check failed: {last_error}")


def run_smoke(*, base_url: str, cloud: str, region: str, timeout: float = 30) -> str:
    if not region:
        raise SmokeError("region must be non-empty")
    if not base_url.startswith(("http://", "https://")):
        raise SmokeError(f"base URL must be http(s): {base_url!r}")
    checked_url = base_url.rstrip("/")
    _wait_for_health(checked_url, timeout)
    payload = json.dumps(
        {"input": "hello from cross-cloud smoke", "cloud": cloud, "region": region}
        | {"metadata": {"smoke": "cross-cloud-nightly"}}
    ).encode()
    request = Request(  # noqa: S310
        f"{checked_url}/v1/turns",
        data=payload,
        headers={"content-type": "application/json", "x-loop-cloud": cloud},
        method="POST",
    )
    response = _read_json(request, timeout=timeout)
    reply = response.get("reply")
    reply_text = cast(dict[str, object], reply).get("text") if isinstance(reply, dict) else None
    received = str(response.get("received", ""))
    if reply_text != "helm-e2e-ok":
        raise SmokeError(f"turn response missing helm-e2e-ok reply: {response!r}")
    if cloud not in received or region not in received:
        raise SmokeError(f"turn response did not echo {cloud}/{region}: {response!r}")
    return f"cross_cloud_smoke: OK cloud={cloud} region={region} base_url={checked_url}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloud", choices=("aws", "azure", "gcp"), required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    try:
        base_url, cloud, region, timeout = args.base_url, args.cloud, args.region, args.timeout
        print(run_smoke(base_url=base_url, cloud=cloud, region=region, timeout=timeout))
    except SmokeError as exc:
        print(f"cross_cloud_smoke: FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
