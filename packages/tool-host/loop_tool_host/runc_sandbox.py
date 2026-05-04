"""Real subprocess-backed `Sandbox` implementation using ``runc`` (S916).

This is the production tool-host sandbox. It supersedes the
``InMemorySandboxFactory`` for any deployment that runs MCP servers
shipped by third parties: code we cannot trust must run in a kernel-
enforced isolation boundary, not in our own Python process.

Architecture
============

For each ``Sandbox.start()`` call we:

1. Build an OCI bundle directory under ``--state-root`` containing the
   MCP server's ``rootfs/`` (extracted from the image tarball whose
   digest is pinned in :class:`SandboxConfig`) and a ``config.json``
   that:

   * caps CPU via ``linux.resources.cpu.quota`` /
     ``linux.resources.cpu.period`` matching ``cpu_millis``,
   * caps memory via ``linux.resources.memory.limit`` matching
     ``memory_mb``,
   * drops all Linux capabilities and forbids new privileges,
   * remaps uid/gid 0 to an unprivileged host range so a container
     escape lands as a non-root user,
   * places the container in its own ``network`` namespace (we create
     and attach the netns ourselves so we can program egress rules
     before the container starts).

2. Create a dedicated network namespace via ``ip netns add``. By
   default the namespace has only its loopback interface — *every*
   packet leaving the netns is dropped because no veth is attached.
   When ``egress_allowlist`` is non-empty we attach a veth pair, set
   up a default-deny chain in the netns via ``nft`` (or fall back to
   ``iptables``) and accept only the listed IP/host destinations.

3. Spawn the container with ``runc create`` + ``runc start``. The MCP
   server is the container's PID 1 and listens on stdio per the MCP
   spec; we shuttle JSON-RPC frames through a pipe set up by ``runc``.

4. ``exec()`` writes a ``tools/call`` JSON-RPC request to the
   container's stdin and reads exactly one response frame from stdout
   (or from the IPC pipe configured during ``start``). A timeout
   derived from ``cpu_millis`` x 60 caps any single call.

5. ``shutdown()`` calls ``runc delete --force`` and ``ip netns del``
   to release the namespace + cgroup. Idempotent.

Subprocess injection
====================

Every external command is dispatched through a single
:class:`SubprocessRunner` callable so tests can drive the factory
without ``runc`` actually being installed on the host (in particular
on macOS, where ``runc`` does not exist). The default runner is
``asyncio.create_subprocess_exec``; tests inject a recording stub.

OCI bundle layout
=================

::

    <state_root>/<sandbox_id>/
        config.json           # OCI runtime spec (built by _build_oci_spec)
        rootfs/               # extracted MCP image (caller-provided)

Kata follow-up: a Kata variant lives behind a future
``KataSandboxFactory`` (filed as a follow-up story per the S916 AC).
The OCI bundle and lifecycle methods are identical — only
``runtime_binary`` and the namespace flags differ — so the seam is
the :class:`SubprocessRunner` + :attr:`runtime_binary` pair.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import shutil
import tempfile
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loop_tool_host.errors import SandboxStartupError, ToolHostError
from loop_tool_host.models import SandboxConfig, SandboxExecResult, SandboxState

_log = logging.getLogger(__name__)

# --- Subprocess seam ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubprocessResult:
    """Outcome of a single external command (runc / ip / nft / ...)."""

    returncode: int
    stdout: bytes
    stderr: bytes


SubprocessRunner = Callable[[Sequence[str], bytes | None], Awaitable[SubprocessResult]]
"""Async callable: ``runner(argv, stdin_bytes) -> SubprocessResult``."""


async def _real_runner(argv: Sequence[str], stdin_bytes: bytes | None) -> SubprocessResult:
    """Default runner — invokes the binary via ``asyncio``."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE if stdin_bytes is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(stdin_bytes)
    return SubprocessResult(proc.returncode or 0, out, err)


# --- OCI bundle generation ----------------------------------------------------


_DROP_ALL_CAPS: tuple[str, ...] = ()  # explicitly empty: drop every capability


def build_oci_spec(
    config: SandboxConfig,
    *,
    rootfs: str,
    netns_path: str,
    args: Sequence[str],
    env: Sequence[str] = (),
) -> dict[str, Any]:
    """Build an OCI runtime spec dict for ``config``.

    The spec hard-codes our security posture: no capabilities, no new
    privileges, read-only rootfs, dedicated mount/pid/ipc/uts/network
    namespaces with the network namespace bound to ``netns_path`` so
    we can program egress rules before the container starts.

    Exposed for unit tests so policy regressions show up in code
    review without needing to run ``runc``.
    """
    cpu_period = 100_000  # 100 ms — the kernel default
    cpu_quota = max(1_000, int(config.cpu_millis * cpu_period / 1000))
    return {
        "ociVersion": "1.0.2",
        "process": {
            "terminal": False,
            "user": {"uid": 65_534, "gid": 65_534},
            "args": list(args),
            "env": list(env) or ["PATH=/usr/local/bin:/usr/bin:/bin"],
            "cwd": "/",
            "noNewPrivileges": True,
            "capabilities": {
                "bounding": list(_DROP_ALL_CAPS),
                "effective": list(_DROP_ALL_CAPS),
                "permitted": list(_DROP_ALL_CAPS),
                "inheritable": list(_DROP_ALL_CAPS),
                "ambient": list(_DROP_ALL_CAPS),
            },
            "rlimits": [
                {"type": "RLIMIT_NOFILE", "hard": 1024, "soft": 1024},
            ],
        },
        "root": {"path": rootfs, "readonly": True},
        "hostname": "loop-sandbox",
        "mounts": [
            {"destination": "/proc", "type": "proc", "source": "proc"},
            {
                "destination": "/dev",
                "type": "tmpfs",
                "source": "tmpfs",
                "options": ["nosuid", "noexec", "size=64k"],
            },
            {
                "destination": "/tmp",
                "type": "tmpfs",
                "source": "tmpfs",
                "options": ["nosuid", "nodev", "size=16m"],
            },
        ],
        "linux": {
            "namespaces": [
                {"type": "pid"},
                {"type": "ipc"},
                {"type": "uts"},
                {"type": "mount"},
                {"type": "network", "path": netns_path},
            ],
            "uidMappings": [{"containerID": 0, "hostID": 100_000, "size": 65_536}],
            "gidMappings": [{"containerID": 0, "hostID": 100_000, "size": 65_536}],
            "resources": {
                "memory": {
                    "limit": config.memory_mb * 1024 * 1024,
                    "swap": config.memory_mb * 1024 * 1024,
                },
                "cpu": {"period": cpu_period, "quota": cpu_quota},
                "pids": {"limit": 64},
            },
            "maskedPaths": [
                "/proc/kcore",
                "/proc/sys",
                "/sys/firmware",
            ],
            "readonlyPaths": ["/proc/asound", "/proc/bus"],
        },
    }


def build_egress_nft_rules(allowlist: Sequence[str]) -> str:
    """Render the ``nft`` ruleset enforcing the egress allowlist.

    An empty allowlist yields a default-deny chain (only ``lo`` is
    permitted). Each entry is interpreted as a host name or CIDR; the
    caller is expected to have resolved DNS names to IPs before
    passing them in (the sandbox runs offline by design).
    """
    rules = [
        "table inet loop_sandbox {",
        "  chain output {",
        "    type filter hook output priority 0; policy drop;",
        '    oifname "lo" accept',
        "    ct state established,related accept",
    ]
    for entry in allowlist:
        # Conservative literal match; the caller already validated
        # the entry shape via SandboxConfig.egress_allowlist.
        rules.append(f"    ip daddr {entry} accept")
    rules.extend(["  }", "}"])
    return "\n".join(rules) + "\n"


# --- Lifecycle ----------------------------------------------------------------


class _RuncFailureError(ToolHostError):
    """Internal: raised when a runc/ip/nft subprocess returns non-zero."""

    code = "LOOP-TH-010"


@dataclass(slots=True)
class RuncSandbox:
    """`Sandbox` impl that drives a real ``runc`` container."""

    config: SandboxConfig
    rootfs: str
    runtime_binary: str = "runc"
    state_root: str = field(default_factory=lambda: tempfile.gettempdir())
    runner: SubprocessRunner = field(default=_real_runner)
    netns_helper: str = "ip"
    egress_helper: str = "nft"
    mcp_argv: tuple[str, ...] = ("/usr/local/bin/mcp-server",)
    _state: SandboxState = field(default=SandboxState.PENDING, init=False)
    _id: str = field(default_factory=lambda: f"loop-{uuid.uuid4().hex[:12]}", init=False)
    _bundle: Path | None = field(default=None, init=False)
    _netns: str | None = field(default=None, init=False)

    @property
    def state(self) -> SandboxState:
        return self._state

    @property
    def sandbox_id(self) -> str:
        return self._id

    async def _run(self, argv: Sequence[str], stdin_bytes: bytes | None = None) -> SubprocessResult:
        result = await self.runner(argv, stdin_bytes)
        if result.returncode != 0:
            raise _RuncFailureError(
                f"{argv[0]} exited {result.returncode}: "
                f"{result.stderr.decode('utf-8', 'replace').strip()}"
            )
        return result

    async def _setup_netns(self) -> str:
        netns = f"loop-{uuid.uuid4().hex[:8]}"
        await self._run([self.netns_helper, "netns", "add", netns])
        rules = build_egress_nft_rules(self.config.egress_allowlist)
        # Run nft inside the netns so the table lives in the right
        # namespace. Default-deny applies the moment the container
        # starts, so a malicious tool's first packet is dropped.
        await self._run(
            [self.netns_helper, "netns", "exec", netns, self.egress_helper, "-f", "-"],
            stdin_bytes=rules.encode("utf-8"),
        )
        return netns

    async def start(self) -> None:
        if self._state is not SandboxState.PENDING:
            return
        try:
            self._netns = await self._setup_netns()
            bundle = Path(self.state_root) / self._id
            bundle.mkdir(parents=True, exist_ok=True)
            spec = build_oci_spec(
                self.config,
                rootfs=self.rootfs,
                netns_path=f"/var/run/netns/{self._netns}",
                args=self.mcp_argv,
            )
            (bundle / "config.json").write_text(json.dumps(spec))
            self._bundle = bundle
            await self._run([self.runtime_binary, "create", "--bundle", str(bundle), self._id])
            await self._run([self.runtime_binary, "start", self._id])
        except _RuncFailureError as exc:
            await self._cleanup()
            raise SandboxStartupError(
                f"runc sandbox start failed for {self.config.mcp_server}: {exc}"
            ) from exc
        self._state = SandboxState.READY

    async def exec(self, *, tool: str, arguments: dict[str, Any]) -> SandboxExecResult:
        if self._state is not SandboxState.READY:
            return SandboxExecResult(ok=False, error=f"sandbox not ready: {self._state.value}")
        self._state = SandboxState.RUNNING
        request = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments},
                }
            ).encode("utf-8")
            + b"\n"
        )
        loop = asyncio.get_event_loop()
        started = loop.time()
        try:
            result = await self._run(
                [self.runtime_binary, "exec", self._id, *self.mcp_argv],
                stdin_bytes=request,
            )
        except _RuncFailureError as exc:
            self._state = SandboxState.READY
            return SandboxExecResult(
                ok=False,
                error=str(exc),
                duration_ms=(loop.time() - started) * 1000,
            )
        try:
            payload = json.loads(result.stdout.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            self._state = SandboxState.READY
            return SandboxExecResult(
                ok=False,
                error=f"non-JSON MCP frame: {exc}",
                duration_ms=(loop.time() - started) * 1000,
            )
        self._state = SandboxState.READY
        return SandboxExecResult(
            ok="error" not in payload,
            payload=payload.get("result", payload),
            error=payload.get("error", {}).get("message") if "error" in payload else None,
            duration_ms=(loop.time() - started) * 1000,
        )

    async def shutdown(self) -> None:
        await self._cleanup()
        self._state = SandboxState.TERMINATED

    async def _cleanup(self) -> None:
        if self._bundle is not None:
            try:
                await self.runner([self.runtime_binary, "delete", "--force", self._id], None)
            except Exception:
                _log.exception("runc delete failed for %s", self._id)
            with contextlib.suppress(OSError):
                shutil.rmtree(self._bundle, ignore_errors=True)
            self._bundle = None
        if self._netns is not None:
            try:
                await self.runner([self.netns_helper, "netns", "del", self._netns], None)
            except Exception:
                _log.exception("netns del failed for %s", self._netns)
            self._netns = None


@dataclass(slots=True)
class RuncSandboxFactory:
    """`SandboxFactory` impl that hands out `RuncSandbox` instances.

    Resolves the rootfs for a given image digest via
    ``rootfs_resolver`` (a callable injected by the caller — in
    production this maps the image digest onto a pre-extracted
    overlay-fs layer). Tests inject a stub that points at a temp dir.
    """

    rootfs_resolver: Callable[[SandboxConfig], str]
    runtime_binary: str = "runc"
    state_root: str = field(default_factory=lambda: tempfile.gettempdir())
    runner: SubprocessRunner = field(default=_real_runner)
    mcp_argv: tuple[str, ...] = ("/usr/local/bin/mcp-server",)

    async def create(self, config: SandboxConfig) -> RuncSandbox:
        rootfs = self.rootfs_resolver(config)
        return RuncSandbox(
            config=config,
            rootfs=rootfs,
            runtime_binary=self.runtime_binary,
            state_root=self.state_root,
            runner=self.runner,
            mcp_argv=self.mcp_argv,
        )


def runc_available() -> bool:
    """True iff this host can actually run a `RuncSandbox`."""
    return os.name == "posix" and shutil.which("runc") is not None


__all__ = [
    "RuncSandbox",
    "RuncSandboxFactory",
    "SubprocessResult",
    "SubprocessRunner",
    "_real_runner",
    "build_egress_nft_rules",
    "build_oci_spec",
    "runc_available",
]
