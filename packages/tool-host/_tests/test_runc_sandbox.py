"""Tests for the runc-backed `Sandbox` impl (S916).

Two layers:

* Unit tests with a recording fake :class:`SubprocessRunner` — these
  always run, including on macOS where ``runc`` is absent.
* Real integration tests that gate on Linux + ``runc`` availability
  (and ``LOOP_TOOL_HOST_RUNC_LIVE=1`` so CI shells without rootless
  privileges don't spuriously fail).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pytest
from loop_tool_host import (
    RuncSandbox,
    RuncSandboxFactory,
    SandboxConfig,
    SandboxStartupError,
    SandboxState,
    runc_available,
)
from loop_tool_host.runc_sandbox import (
    SubprocessResult,
    build_egress_nft_rules,
    build_oci_spec,
)

_BASE_CONFIG = SandboxConfig(
    workspace_id="ws-1",
    mcp_server="echo",
    image_digest="sha256:" + "a" * 64,
    cpu_millis=500,
    memory_mb=128,
    egress_allowlist=(),
)


class _RecordingRunner:
    """Fake `SubprocessRunner` capturing every invocation."""

    def __init__(
        self,
        responses: dict[str, SubprocessResult] | None = None,
    ) -> None:
        self.calls: list[tuple[tuple[str, ...], bytes | None]] = []
        self._responses = responses or {}

    async def __call__(self, argv: Sequence[str], stdin_bytes: bytes | None) -> SubprocessResult:
        argv_t = tuple(argv)
        self.calls.append((argv_t, stdin_bytes))
        # Match by (binary, first verb).
        key = f"{argv_t[0]}:{argv_t[1] if len(argv_t) > 1 else ''}"
        return self._responses.get(key, SubprocessResult(0, b"", b""))


def test_oci_spec_enforces_security_posture() -> None:
    spec = build_oci_spec(
        _BASE_CONFIG,
        rootfs="/tmp/rfs",  # noqa: S108
        netns_path="/var/run/netns/x",
        args=("/bin/echo",),
    )
    assert spec["process"]["noNewPrivileges"] is True
    assert spec["process"]["capabilities"]["bounding"] == []
    assert spec["root"]["readonly"] is True
    assert spec["linux"]["resources"]["memory"]["limit"] == 128 * 1024 * 1024
    assert spec["linux"]["resources"]["cpu"]["quota"] == 50_000  # 500m * 100k / 1000
    netns = next(ns for ns in spec["linux"]["namespaces"] if ns["type"] == "network")
    assert netns["path"] == "/var/run/netns/x"


def test_oci_spec_user_remap_drops_root_to_unprivileged_host_uid() -> None:
    spec = build_oci_spec(
        _BASE_CONFIG,
        rootfs="/tmp/rfs",  # noqa: S108
        netns_path="/var/run/netns/x",
        args=("/x",),
    )
    [uid_map] = spec["linux"]["uidMappings"]
    assert uid_map["containerID"] == 0
    assert uid_map["hostID"] >= 100_000


def test_egress_nft_rules_default_deny_when_allowlist_empty() -> None:
    out = build_egress_nft_rules(())
    assert "policy drop" in out
    assert "ip daddr" not in out  # no accept rules


def test_egress_nft_rules_emit_one_accept_per_allowlist_entry() -> None:
    out = build_egress_nft_rules(("10.0.0.5", "192.168.1.0/24"))
    assert out.count("ip daddr") == 2
    assert "10.0.0.5 accept" in out


def _make_sandbox(runner: _RecordingRunner, allowlist: tuple[str, ...] = ()) -> RuncSandbox:
    cfg = _BASE_CONFIG.model_copy(update={"egress_allowlist": allowlist})
    return RuncSandbox(
        config=cfg,
        rootfs="/tmp/rootfs-stub",  # noqa: S108
        state_root=tempfile.mkdtemp(prefix="loop-test-"),
        runner=runner,
        mcp_argv=("/bin/echo-mcp",),
    )


def test_start_invokes_netns_runc_and_writes_oci_bundle() -> None:
    runner = _RecordingRunner()
    sb = _make_sandbox(runner)
    asyncio.run(sb.start())
    assert sb.state is SandboxState.READY
    binaries = [c[0][0] for c in runner.calls]
    assert binaries[:2] == ["ip", "ip"]  # netns add, then nft via netns exec
    assert "runc" in binaries and binaries[-1] == "runc"
    bundle = Path(sb._bundle)  # type: ignore[arg-type]
    assert (bundle / "config.json").exists()
    spec = json.loads((bundle / "config.json").read_text())
    assert spec["process"]["args"] == ["/bin/echo-mcp"]


def test_start_default_deny_egress_emits_drop_policy_to_nft() -> None:
    runner = _RecordingRunner()
    sb = _make_sandbox(runner)
    asyncio.run(sb.start())
    nft_calls = [c for c in runner.calls if "nft" in c[0]]
    assert nft_calls, "nft must be invoked inside the netns"
    nft_input = nft_calls[0][1] or b""
    assert b"policy drop" in nft_input
    assert b"ip daddr" not in nft_input  # empty allowlist


def test_start_nonzero_runc_create_raises_sandbox_startup_error() -> None:
    runner = _RecordingRunner(
        responses={"runc:create": SubprocessResult(1, b"", b"runc: bundle invalid")}
    )
    sb = _make_sandbox(runner)
    with pytest.raises(SandboxStartupError, match="runc sandbox start failed"):
        asyncio.run(sb.start())
    assert sb.state is SandboxState.PENDING
    # cleanup attempted: netns del + runc delete should have been invoked
    cleanup_argv = [c[0] for c in runner.calls]
    assert any("delete" in argv for argv in cleanup_argv)


def test_exec_marshals_jsonrpc_and_returns_payload() -> None:
    rpc_response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"echo": "hi"}}).encode("utf-8")
    runner = _RecordingRunner(responses={"runc:exec": SubprocessResult(0, rpc_response, b"")})
    sb = _make_sandbox(runner)
    asyncio.run(sb.start())
    result = asyncio.run(sb.exec(tool="echo", arguments={"msg": "hi"}))
    assert result.ok
    assert result.payload == {"echo": "hi"}
    # exec call wrote a tools/call frame on stdin
    exec_call = next(c for c in runner.calls if c[0][:2] == ("runc", "exec"))
    body = json.loads((exec_call[1] or b"").decode("utf-8"))
    assert body["method"] == "tools/call"
    assert body["params"] == {"name": "echo", "arguments": {"msg": "hi"}}
    assert sb.state is SandboxState.READY


def test_exec_returns_error_when_runc_fails() -> None:
    runner = _RecordingRunner(responses={"runc:exec": SubprocessResult(2, b"", b"oom")})
    sb = _make_sandbox(runner)
    asyncio.run(sb.start())
    result = asyncio.run(sb.exec(tool="bad", arguments={}))
    assert not result.ok
    assert "oom" in (result.error or "")
    assert sb.state is SandboxState.READY


def test_exec_rejects_calls_when_not_ready() -> None:
    runner = _RecordingRunner()
    sb = _make_sandbox(runner)
    result = asyncio.run(sb.exec(tool="x", arguments={}))
    assert not result.ok
    assert "not ready" in (result.error or "")


def test_shutdown_invokes_runc_delete_and_netns_del() -> None:
    runner = _RecordingRunner()
    sb = _make_sandbox(runner)
    asyncio.run(sb.start())
    asyncio.run(sb.shutdown())
    assert sb.state is SandboxState.TERMINATED
    argvs = [c[0] for c in runner.calls]
    assert any(a[:2] == ("runc", "delete") for a in argvs)
    assert any(a[:3] == ("ip", "netns", "del") for a in argvs)


def test_factory_resolves_rootfs_per_config() -> None:
    runner = _RecordingRunner()
    seen: list[str] = []

    def resolver(cfg: SandboxConfig) -> str:
        seen.append(cfg.image_digest)
        return f"/var/lib/loop/rootfs/{cfg.image_digest}"

    factory = RuncSandboxFactory(rootfs_resolver=resolver, runner=runner)
    sb = asyncio.run(factory.create(_BASE_CONFIG))
    assert sb.rootfs.endswith(_BASE_CONFIG.image_digest)
    assert seen == [_BASE_CONFIG.image_digest]


# --- Real integration tests ---------------------------------------------------


_RUNC_LIVE = runc_available() and os.environ.get("LOOP_TOOL_HOST_RUNC_LIVE") == "1"


@pytest.mark.skipif(
    not _RUNC_LIVE,
    reason="runc unavailable or LOOP_TOOL_HOST_RUNC_LIVE!=1",
)
def test_live_echo_tool_returns_payload_inside_runc() -> None:
    """Integration: spawn a real runc container, exec an echo MCP tool."""
    rootfs = tempfile.mkdtemp(prefix="loop-rootfs-")
    # Minimal busybox-style rootfs setup is a host-prep concern; this
    # test only runs in CI where the rootfs is staged by the workflow.
    staged = os.environ.get("LOOP_TOOL_HOST_TEST_ROOTFS")
    if not staged:
        pytest.skip("LOOP_TOOL_HOST_TEST_ROOTFS not set")
    shutil.rmtree(rootfs)
    sb = RuncSandbox(config=_BASE_CONFIG, rootfs=staged, mcp_argv=("/bin/echo-mcp",))
    asyncio.run(sb.start())
    try:
        result = asyncio.run(sb.exec(tool="echo", arguments={"msg": "hi"}))
        assert result.ok, result.error
    finally:
        asyncio.run(sb.shutdown())


@pytest.mark.skipif(
    not _RUNC_LIVE,
    reason="runc unavailable or LOOP_TOOL_HOST_RUNC_LIVE!=1",
)
def test_live_malicious_egress_is_blocked_by_default_deny_netns() -> None:
    """Integration: a tool that tries network egress is dropped by nft."""
    staged = os.environ.get("LOOP_TOOL_HOST_TEST_ROOTFS")
    if not staged:
        pytest.skip("LOOP_TOOL_HOST_TEST_ROOTFS not set")
    sb = RuncSandbox(
        config=_BASE_CONFIG,
        rootfs=staged,
        mcp_argv=("/bin/malicious-egress",),
    )
    asyncio.run(sb.start())
    try:
        result = asyncio.run(sb.exec(tool="exfiltrate", arguments={"to": "1.1.1.1"}))
        # Either the exec returns an error payload, or the tool exits
        # non-zero. In both cases ok must be False.
        assert not result.ok
    finally:
        asyncio.run(sb.shutdown())
