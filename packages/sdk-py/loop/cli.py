"""Loop CLI v0.

This module is intentionally network-agnostic: command handlers depend on a
small ``ControlPlaneTransport`` Protocol, and tests inject an in-memory fake.
The default transport raises until the real cp-api HTTP binding lands.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TextIO

import httpx
from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    workspace_id: str | None = None
    expires_at: int | None = Field(default=None, ge=0)


class DeployBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str
    sha256: str
    size_bytes: int = Field(ge=0)


class ReleaseArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    platform: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: str = Field(min_length=1)
    artifacts: tuple[ReleaseArtifact, ...]


class ControlPlaneTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]: ...

    def stream(
        self,
        path: str,
        *,
        token: str | None = None,
    ) -> Iterable[str]: ...


class OfflineTransport:
    """Default placeholder until a real HTTP transport is wired."""

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        raise RuntimeError(f"no control-plane transport configured for {method} {path}")

    def stream(
        self,
        path: str,
        *,
        token: str | None = None,
    ) -> Iterable[str]:
        raise RuntimeError(f"no control-plane transport configured for stream {path}")


class ControlPlaneTransportError(RuntimeError):
    """Raised when the cp-api returns a non-2xx response."""

    def __init__(self, status_code: int, method: str, path: str, body: str) -> None:
        super().__init__(f"{method} {path} -> HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        self.method = method
        self.path = path
        self.body = body


class HttpxControlPlaneTransport:
    """Real cp-api transport over httpx (S903).

    Replaces OfflineTransport when LOOP_CP_API_URL is set. Issues JSON
    requests against the control-plane FastAPI app (S901) and streams
    SSE/log lines for the ``stream`` contract.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("HttpxControlPlaneTransport requires a non-empty base_url")
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpxControlPlaneTransport:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _headers(self, token: str | None) -> dict[str, str]:
        headers: dict[str, str] = {"accept": "application/json"}
        if token:
            headers["authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else path
        response = self._client.request(
            method.upper(),
            url,
            json=json_body,
            headers=self._headers(token),
        )
        if response.status_code >= 400:
            raise ControlPlaneTransportError(
                response.status_code, method.upper(), path, response.text
            )
        if not response.content:
            return {}
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ControlPlaneTransportError(
                response.status_code, method.upper(), path, response.text
            ) from exc
        if not isinstance(payload, dict):
            return {"data": payload}
        return payload

    def stream(
        self,
        path: str,
        *,
        token: str | None = None,
    ) -> Iterable[str]:
        with self._client.stream("GET", path, headers=self._headers(token)) as response:
            if response.status_code >= 400:
                body = response.read().decode("utf-8", errors="replace")
                raise ControlPlaneTransportError(
                    response.status_code, "GET", path, body
                )
            for line in response.iter_lines():
                if line:
                    yield line


def default_transport() -> ControlPlaneTransport:
    """Return the real httpx transport when LOOP_CP_API_URL is set.

    Falls back to OfflineTransport so unit tests and ``loop init`` (which
    needs no network) keep working without configuration.
    """
    base_url = os.environ.get("LOOP_CP_API_URL")
    if not base_url:
        return OfflineTransport()
    timeout = float(os.environ.get("LOOP_CP_API_TIMEOUT", "30"))
    return HttpxControlPlaneTransport(base_url, timeout=timeout)


@dataclass(frozen=True)
class CliContext:
    transport: ControlPlaneTransport
    home: Path
    out: TextIO

    @property
    def credentials_path(self) -> Path:
        return self.home / ".loop" / "credentials"


def save_credentials(path: Path, credentials: Credentials) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.model_dump_json(indent=2), encoding="utf-8")
    path.chmod(0o600)


def load_credentials(path: Path) -> Credentials:
    return Credentials.model_validate_json(path.read_text(encoding="utf-8"))


def completion_script(shell: str) -> str:
    if shell not in {"bash", "zsh", "fish"}:
        raise ValueError("shell must be bash, zsh, or fish")
    commands = "login init deploy logs eval secrets release"
    if shell == "fish":
        return f"complete -c loop -f -a '{commands}'\n"
    return f"_loop_complete() {{ COMPREPLY=($(compgen -W '{commands}' -- \"$2\")); }}\ncomplete -F _loop_complete loop\n"


def bundle_project(path: Path) -> DeployBundle:
    if not path.is_dir():
        raise ValueError(f"{path}: not a directory")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(p for p in path.rglob("*") if p.is_file()):
            if ".git" in file.parts:
                continue
            zf.write(file, file.relative_to(path))
    payload = buf.getvalue()
    return DeployBundle(
        path=str(path),
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )


def build_release_manifest(version: str, artifacts: Iterable[Path]) -> ReleaseManifest:
    rows: list[ReleaseArtifact] = []
    for artifact in artifacts:
        data = artifact.read_bytes()
        platform = artifact.stem.removeprefix("loop-")
        rows.append(
            ReleaseArtifact(
                platform=platform,
                path=str(artifact),
                sha256=hashlib.sha256(data).hexdigest(),
                size_bytes=len(data),
            )
        )
    return ReleaseManifest(version=version, artifacts=tuple(rows))


def scaffold_agent(path: Path, *, agent_name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "agent.yaml").write_text(
        "name: " + agent_name + "\nmodel: loop:smart\nskills:\n  - support\n",
        encoding="utf-8",
    )
    (path / "agent.py").write_text(
        "from loop import AgentResponse, ContentPart\n\n"
        "async def handle(event):\n"
        "    text = event.content[0].text or ''\n"
        "    return AgentResponse(\n"
        "        conversation_id=event.conversation_id,\n"
        "        content=[ContentPart(type='text', text=f'echo: {text}')],\n"
        "    )\n",
        encoding="utf-8",
    )
    eval_dir = path / "evals"
    eval_dir.mkdir(exist_ok=True)
    (eval_dir / "smoke.yaml").write_text(
        "suite: smoke\nsamples:\n  - id: hello\n    input: hello\n    expected: 'echo: hello'\n",
        encoding="utf-8",
    )


def _token(ctx: CliContext) -> str | None:
    if not ctx.credentials_path.exists():
        return None
    return load_credentials(ctx.credentials_path).access_token


def _cmd_login(args: argparse.Namespace, ctx: CliContext) -> int:
    start = ctx.transport.request("POST", "/auth/device-code")
    print(f"Open {start['verification_url']} and enter code {start['user_code']}", file=ctx.out)
    token = ctx.transport.request(
        "POST",
        "/auth/device-token",
        json_body={"device_code": start["device_code"]},
    )
    credentials = Credentials(
        access_token=str(token["access_token"]),
        refresh_token=str(token["refresh_token"]),
        workspace_id=token.get("workspace_id"),
        expires_at=token.get("expires_at"),
    )
    save_credentials(ctx.credentials_path, credentials)
    print(f"Logged in. Credentials written to {ctx.credentials_path}", file=ctx.out)
    return 0


def _cmd_init(args: argparse.Namespace, ctx: CliContext) -> int:
    scaffold_agent(Path(args.path), agent_name=args.name)
    print(f"Created Loop agent at {args.path}", file=ctx.out)
    return 0


def _cmd_deploy(args: argparse.Namespace, ctx: CliContext) -> int:
    token = _token(ctx)
    bundle = bundle_project(Path(args.path))
    response = ctx.transport.request(
        "POST",
        "/agents/deployments",
        json_body={
            "path": bundle.path,
            "sha256": bundle.sha256,
            "size_bytes": bundle.size_bytes,
        },
        token=token,
    )
    deploy_id = str(response.get("id", "unknown"))
    status = str(response.get("status", "accepted"))
    pollable = {"pending", "queued", "running"}
    for _ in range(args.polls):
        if status not in pollable or deploy_id == "unknown":
            break
        response = ctx.transport.request(
            "GET",
            f"/agents/deployments/{deploy_id}",
            token=token,
        )
        status = str(response.get("status", status))
    print(f"Deploy {deploy_id}: {status}", file=ctx.out)
    return 0 if status not in {"failed", "error"} else 1


def _cmd_logs(args: argparse.Namespace, ctx: CliContext) -> int:
    path = f"/logs/{args.agent_id}"
    if args.conversation_id:
        path += f"?conversation_id={args.conversation_id}"
    try:
        for line in ctx.transport.stream(path, token=_token(ctx)):
            print(line.rstrip("\n"), file=ctx.out)
            if not args.follow:
                break
    except KeyboardInterrupt:
        print("Log stream stopped.", file=ctx.out)
    return 0


def _cmd_eval(args: argparse.Namespace, ctx: CliContext) -> int:
    response = ctx.transport.request(
        "POST",
        f"/eval-suites/{args.suite}/runs",
        json_body={"agent_version_id": args.agent_version},
        token=_token(ctx),
    )
    status = str(response.get("status", "unknown"))
    print(f"ok 1 - remote eval {args.suite} status={status}", file=ctx.out)
    return 0 if status in {"passed", "running", "pending"} else 1


def _cmd_secrets(args: argparse.Namespace, ctx: CliContext) -> int:
    token = _token(ctx)
    if args.action == "list":
        response = ctx.transport.request("GET", "/secrets", token=token)
        for item in response.get("secrets", []):
            print(str(item.get("name", item)), file=ctx.out)
        return 0
    if args.action == "set":
        ctx.transport.request(
            "POST",
            "/secrets",
            json_body={"name": args.name, "value": args.value},
            token=token,
        )
        print(f"Secret {args.name} stored", file=ctx.out)
        return 0
    if args.action == "get":
        ctx.transport.request("GET", f"/secrets/{args.name}", token=token)
        print(f"Secret {args.name}: value hidden", file=ctx.out)
        return 0
    if args.action == "rotate":
        ctx.transport.request("POST", f"/secrets/{args.name}/rotate", token=token)
        print(f"Secret {args.name} rotated", file=ctx.out)
        return 0
    raise ValueError(f"unknown secrets action: {args.action}")


def _cmd_release(args: argparse.Namespace, ctx: CliContext) -> int:
    manifest = build_release_manifest(args.version, [Path(p) for p in args.artifacts])
    if args.publish:
        ctx.transport.request(
            "POST",
            "/releases",
            json_body=manifest.model_dump(mode="json"),
            token=_token(ctx),
        )
    print(manifest.model_dump_json(indent=2), file=ctx.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loop")
    parser.add_argument("--install-completion", choices=("bash", "zsh", "fish"))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("login")

    p_init = sub.add_parser("init")
    p_init.add_argument("path")
    p_init.add_argument("--name", default="support-agent")

    p_deploy = sub.add_parser("deploy")
    p_deploy.add_argument("path")
    p_deploy.add_argument("--polls", type=int, default=5)

    p_logs = sub.add_parser("logs")
    p_logs.add_argument("agent_id")
    p_logs.add_argument("--conversation-id")
    p_logs.add_argument("--follow", action="store_true")

    p_eval = sub.add_parser("eval")
    eval_sub = p_eval.add_subparsers(dest="eval_command")
    p_eval_run = eval_sub.add_parser("run")
    p_eval_run.add_argument("suite")
    p_eval_run.add_argument("--agent-version", default="latest")

    p_secrets = sub.add_parser("secrets")
    secrets_sub = p_secrets.add_subparsers(dest="action")
    secrets_sub.add_parser("list")
    p_secret_set = secrets_sub.add_parser("set")
    p_secret_set.add_argument("name")
    p_secret_set.add_argument("value")
    p_secret_get = secrets_sub.add_parser("get")
    p_secret_get.add_argument("name")
    p_secret_rotate = secrets_sub.add_parser("rotate")
    p_secret_rotate.add_argument("name")

    p_release = sub.add_parser("release")
    p_release.add_argument("version")
    p_release.add_argument("artifacts", nargs="+")
    p_release.add_argument("--publish", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    transport: ControlPlaneTransport | None = None,
    home: Path | None = None,
    out: TextIO | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = out or sys.stdout
    if args.install_completion:
        print(completion_script(args.install_completion), file=out, end="")
        return 0
    ctx = CliContext(
        transport=transport or default_transport(),
        home=home or Path.home(),
        out=out,
    )
    if args.command == "login":
        return _cmd_login(args, ctx)
    if args.command == "init":
        return _cmd_init(args, ctx)
    if args.command == "deploy":
        return _cmd_deploy(args, ctx)
    if args.command == "logs":
        return _cmd_logs(args, ctx)
    if args.command == "eval" and args.eval_command == "run":
        return _cmd_eval(args, ctx)
    if args.command == "secrets" and args.action:
        return _cmd_secrets(args, ctx)
    if args.command == "release":
        return _cmd_release(args, ctx)
    parser.print_help(out)
    return 2


__all__ = [
    "ControlPlaneTransport",
    "ControlPlaneTransportError",
    "Credentials",
    "DeployBundle",
    "HttpxControlPlaneTransport",
    "OfflineTransport",
    "ReleaseArtifact",
    "ReleaseManifest",
    "build_parser",
    "build_release_manifest",
    "bundle_project",
    "completion_script",
    "default_transport",
    "load_credentials",
    "main",
    "save_credentials",
    "scaffold_agent",
]
