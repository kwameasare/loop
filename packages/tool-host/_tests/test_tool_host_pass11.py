# ruff: noqa: S105
"""Pass11 tool-host tests: MCP governance and runtime orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from loop_tool_host import InMemorySandbox, SandboxConfig
from loop_tool_host.mcp_governance import (
    EgressPolicy,
    EgressRule,
    SecretInjector,
    SecretReference,
    SignedToolVerifier,
    ToolKillSwitchRegistry,
    ToolObserver,
    ToolPolicy,
    ToolQuota,
    ToolRevokeEvent,
    ToolSignature,
)
from loop_tool_host.mcp_runtime import (
    HotRestartPlanner,
    InboundMcpServer,
    McpProtocolNegotiationError,
    McpProtocolNegotiator,
    PoolDemand,
    RuntimeToolDescriptor,
    ToolCall,
    ToolConfigVersion,
    ToolExecutor,
    ToolVersion,
    ToolVersionRegistry,
    WarmPoolController,
)


def _sandbox_config() -> SandboxConfig:
    return SandboxConfig(
        workspace_id="ws-pass11",
        mcp_server="loop-tools",
        image_digest="sha256:" + "b" * 64,
    )


def test_tool_policy_allow_deny_and_scopes() -> None:
    policy = ToolPolicy(
        allowed_tools=("salesforce.*", "search"),
        denied_tools=("salesforce.delete",),
        required_scopes={"salesforce.query": ("crm:read",)},
    )
    assert policy.authorize(tool="search", scopes=()).allowed
    denied = policy.authorize(tool="salesforce.delete", scopes=("crm:write",))
    assert not denied.allowed
    assert denied.code == "LOOP-TH-101"

    missing = policy.authorize(tool="salesforce.query", scopes=())
    assert not missing.allowed
    assert missing.missing_scopes == ("crm:read",)
    assert policy.authorize(tool="salesforce.query", scopes=("crm:read",)).allowed


def test_egress_policy_allows_exact_and_subdomain_hosts() -> None:
    policy = EgressPolicy(
        rules=(
            EgressRule(host="api.salesforce.com", ports=(443,)),
            EgressRule(host="zendesk.com", ports=(443,), allow_subdomains=True),
        )
    )
    assert policy.authorize_url(tool="crm", url="https://api.salesforce.com/v1").allowed
    assert policy.authorize_url(tool="support", url="https://acme.zendesk.com/tickets").allowed

    denied = policy.authorize_url(tool="crm", url="https://evil.example/v1")
    assert not denied.allowed
    assert denied.code == "LOOP-TH-201"

    private = policy.authorize_url(tool="crm", url="http://127.0.0.1:8080/admin")
    assert not private.allowed
    assert "private-host" in private.reason


def test_secret_injector_decrypts_boot_env_and_redacts_logs() -> None:
    injector = SecretInjector(_FakeKms({"cipher:a": "plain-token"}))
    env = injector.inject(
        (
            SecretReference(
                name="salesforce",
                env_name="SALESFORCE_TOKEN",
                ciphertext="cipher:a",
            ),
        )
    )
    assert env.env["SALESFORCE_TOKEN"] == "plain-token"
    assert env.redacted["SALESFORCE_TOKEN"] == "***"


@pytest.mark.asyncio
async def test_tool_executor_applies_policy_and_timeout() -> None:
    async def slow(tool: str, arguments: dict[str, object]) -> object:
        await asyncio.sleep(0.2)
        return {"tool": tool, "args": arguments}

    sandbox = InMemorySandbox(_sandbox_config(), slow)
    await sandbox.start()
    executor = ToolExecutor(sandbox, policy=ToolPolicy(allowed_tools=("search",)))

    blocked = await executor.execute(ToolCall(workspace_id="ws", agent_id="a", tool="delete"))
    assert not blocked.ok
    assert blocked.error_code == "LOOP-TH-101"

    timeout = await executor.execute(
        ToolCall(workspace_id="ws", agent_id="a", tool="search", timeout_ms=100)
    )
    assert not timeout.ok
    assert timeout.error_code == "LOOP-TH-401"


@pytest.mark.asyncio
async def test_tool_executor_propagates_cancellation_by_shutdown() -> None:
    release = asyncio.Event()

    async def wait_forever(tool: str, arguments: dict[str, object]) -> object:
        await release.wait()
        return {"done": True}

    sandbox = InMemorySandbox(_sandbox_config(), wait_forever)
    await sandbox.start()
    task = asyncio.create_task(
        ToolExecutor(sandbox).execute(ToolCall(workspace_id="ws", agent_id="a", tool="search"))
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()


def test_warm_pool_controller_reconciles_demand() -> None:
    controller = WarmPoolController()
    up = controller.plan(
        PoolDemand(
            workspace_id="ws",
            tool="search",
            in_flight=2,
            idle=0,
            queued=3,
            min_idle=1,
            max_size=6,
        )
    )
    assert up.action == "scale-up"
    assert up.target_idle == 4

    down = controller.plan(
        PoolDemand(
            workspace_id="ws",
            tool="search",
            in_flight=0,
            idle=5,
            queued=0,
            min_idle=2,
            max_size=6,
        )
    )
    assert down.action == "scale-down"
    assert down.target_idle == 2


def test_hot_restart_planner_and_quota_limits() -> None:
    quota = ToolQuota(cpu_millis=500, memory_mb=256, disk_mb=128, timeout_ms=10_000)
    old = ToolConfigVersion(tool="search", version="1", config_digest="sha256:old", quota=quota)
    new = ToolConfigVersion(tool="search", version="2", config_digest="sha256:new", quota=quota)
    plan = HotRestartPlanner().plan(old=old, new=new, in_flight_calls=2)
    assert plan.restart_required
    assert "drain" in plan.reason
    assert quota.as_cgroup_limits()["memory.max"] == "256M"


def test_mcp_protocol_negotiator_picks_highest_common_version() -> None:
    negotiated = McpProtocolNegotiator(("2024.11", "2025.03", "2025.06")).negotiate(
        ("2025.03", "2024.11")
    )
    assert negotiated.version == "2025.03"
    assert negotiated.downgraded

    with pytest.raises(McpProtocolNegotiationError) as exc:
        McpProtocolNegotiator(("2025.06",)).negotiate(("2024.11",))
    assert exc.value.code == "LOOP-TH-601"


@pytest.mark.asyncio
async def test_inbound_mcp_server_lists_and_dispatches_runtime_tools() -> None:
    handler = _FakeRuntimeHandler()
    server = InboundMcpServer(
        (
            RuntimeToolDescriptor(
                name="loop.turns.create",
                description="Create a runtime turn",
                input_schema={"type": "object"},
            ),
        ),
        handler,
        policy=ToolPolicy(
            allowed_tools=("loop.turns.create",),
            required_scopes={"loop.turns.create": ("turns:write",)},
        ),
    )
    assert server.list_tools()[0].name == "loop.turns.create"

    blocked = await server.call_tool(
        name="loop.turns.create",
        arguments={},
        scopes=(),
    )
    assert not blocked.ok

    ok = await server.call_tool(
        name="loop.turns.create",
        arguments={"conversation_id": "c1"},
        scopes=("turns:write",),
    )
    assert ok.ok
    assert ok.payload == {"name": "loop.turns.create", "conversation_id": "c1"}


def test_tool_version_registry_stage_publish_and_rollback() -> None:
    registry = ToolVersionRegistry()
    v1 = ToolVersion(
        tool="search",
        version="1",
        image_digest="sha256:1",
        manifest_digest="sha256:m1",
        published_ms=100,
    )
    v2 = ToolVersion(
        tool="search",
        version="2",
        image_digest="sha256:2",
        manifest_digest="sha256:m2",
        published_ms=200,
    )
    registry.stage(v1)
    registry.stage(v2)
    assert registry.publish(tool="search", version="1").version == "1"
    assert registry.publish(tool="search", version="2").version == "2"
    assert registry.active("search").version == "2"
    assert registry.rollback("search").version == "1"


def test_signed_tool_verifier_and_kill_switch() -> None:
    verifier = SignedToolVerifier(_FakeSignatureVerifier(valid=True))
    signature = ToolSignature(
        publisher="loop",
        image_digest="sha256:image",
        manifest_digest="sha256:manifest",
        signature="sig",
    )
    assert verifier.verify(tool="search", signature=signature).allowed

    denied = SignedToolVerifier(_FakeSignatureVerifier(valid=False)).verify(
        tool="search",
        signature=signature,
    )
    assert not denied.allowed
    assert denied.code == "LOOP-TH-501"

    registry = ToolKillSwitchRegistry()
    registry.revoke(
        ToolRevokeEvent(
            tool="search",
            reason="hostile behavior",
            issued_ms=1_000,
            drain_deadline_ms=61_000,
        )
    )
    assert registry.is_revoked("search")
    assert not registry.should_terminate(tool="search", now_ms=60_000)
    assert registry.should_terminate(tool="search", now_ms=61_000)


def test_tool_observer_hashes_redacted_payloads_without_raw_pii() -> None:
    observer = ToolObserver()
    span = observer.record(
        trace_id="trace-1",
        workspace_id="ws",
        agent_id="agent",
        tool="zendesk.create",
        args={"email": "user@example.com"},
        result={"phone": "+1 415 555 1212"},
        duration_ms=42,
    )
    assert span.redacted
    assert len(span.args_hash) == 64
    assert len(span.result_hash) == 64
    assert observer.spans == (span,)
    assert "user@example.com" not in span.args_hash


@dataclass(frozen=True, slots=True)
class _FakeKms:
    values: dict[str, str]

    def decrypt(self, ciphertext: str) -> str:
        return self.values[ciphertext]


@dataclass(frozen=True, slots=True)
class _FakeSignatureVerifier:
    valid: bool

    def verify(self, signature: ToolSignature) -> bool:
        return self.valid and signature.signature == "sig"


class _FakeRuntimeHandler:
    async def invoke(self, name: str, arguments: dict[str, object]) -> object:
        return {"name": name, **arguments}
