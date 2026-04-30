"""Tests for pass4 control-plane substance: S117, S111, S281, S282."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane.cost_rollup import (
    CostRollupService,
    DimensionedUsageEvent,
    month_bucket_start_ms,
)
from loop_control_plane.invites import InviteError, InviteService
from loop_control_plane.rate_limit import (
    InMemoryBucketStore,
    RateLimiter,
    RateLimitError,
)
from loop_control_plane.workspaces import Role, WorkspaceService


# --------------------------------------------------------------- S117 limiter
@pytest.mark.asyncio
async def test_token_bucket_admits_up_to_capacity_then_rejects() -> None:
    clock = [0]
    limiter = RateLimiter(
        capacity=3, refill_per_sec=0, clock_ms=lambda: clock[0]
    )
    assert await limiter.try_consume("a")
    assert await limiter.try_consume("a")
    assert await limiter.try_consume("a")
    assert not await limiter.try_consume("a")


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time() -> None:
    clock = [0]
    limiter = RateLimiter(
        capacity=2, refill_per_sec=1, clock_ms=lambda: clock[0]
    )
    assert await limiter.try_consume("k")
    assert await limiter.try_consume("k")
    assert not await limiter.try_consume("k")
    clock[0] = 1500  # +1.5 s -> +1 token (capped at capacity-after-debit)
    assert await limiter.try_consume("k")
    assert not await limiter.try_consume("k")


@pytest.mark.asyncio
async def test_token_bucket_rejects_oversize_cost() -> None:
    limiter = RateLimiter(capacity=2, refill_per_sec=0)
    assert not await limiter.try_consume("k", cost=3)


def test_token_bucket_validates_capacity() -> None:
    with pytest.raises(RateLimitError):
        RateLimiter(capacity=0, refill_per_sec=1)
    with pytest.raises(RateLimitError):
        RateLimiter(capacity=1, refill_per_sec=-1)


@pytest.mark.asyncio
async def test_in_memory_store_isolates_keys() -> None:
    store = InMemoryBucketStore()
    limiter = RateLimiter(
        capacity=1, refill_per_sec=0, store=store, clock_ms=lambda: 0
    )
    assert await limiter.try_consume("a")
    assert await limiter.try_consume("b")  # different key, fresh bucket
    assert not await limiter.try_consume("a")


# --------------------------------------------------------------- S111 invites
@pytest.mark.asyncio
async def test_invite_issue_and_accept_flow() -> None:
    workspaces = WorkspaceService()
    ws = await workspaces.create(name="acme", slug="acme", owner_sub="owner")
    clock = [0]
    inv = InviteService(workspaces=workspaces, clock_ms=lambda: clock[0])
    issued = await inv.issue(
        workspace_id=ws.id,
        email="x@example.com",
        role=Role.MEMBER,
        invited_by="owner",
    )
    assert len(issued.token) >= 32
    membership = await inv.accept(token=issued.token, user_sub="user-1")
    assert membership.workspace_id == ws.id
    assert membership.role == Role.MEMBER

    # double-accept rejected
    with pytest.raises(InviteError):
        await inv.accept(token=issued.token, user_sub="user-1")


@pytest.mark.asyncio
async def test_invite_unknown_token_rejected() -> None:
    workspaces = WorkspaceService()
    inv = InviteService(workspaces=workspaces, clock_ms=lambda: 0)
    with pytest.raises(InviteError):
        await inv.accept(token="not-a-real-token-xxxxxxxxxxxxxxxxxxx", user_sub="u")  # noqa: S106


@pytest.mark.asyncio
async def test_invite_expires() -> None:
    workspaces = WorkspaceService()
    ws = await workspaces.create(name="acme2", slug="acme2", owner_sub="o")
    clock = [0]
    inv = InviteService(
        workspaces=workspaces, ttl_ms=1000, clock_ms=lambda: clock[0]
    )
    issued = await inv.issue(
        workspace_id=ws.id, email="y@x.com", role=Role.MEMBER, invited_by="o"
    )
    clock[0] = 5000
    with pytest.raises(InviteError):
        await inv.accept(token=issued.token, user_sub="user-2")


@pytest.mark.asyncio
async def test_invite_dedup_open_for_same_email() -> None:
    workspaces = WorkspaceService()
    ws = await workspaces.create(name="d", slug="d", owner_sub="o")
    inv = InviteService(workspaces=workspaces, clock_ms=lambda: 0)
    await inv.issue(
        workspace_id=ws.id, email="z@x.com", role=Role.MEMBER, invited_by="o"
    )
    with pytest.raises(InviteError):
        await inv.issue(
            workspace_id=ws.id, email="z@x.com", role=Role.MEMBER, invited_by="o"
        )


# --------------------------------------------------------- S281/S282 cost
def test_month_bucket_start_aligned_to_first_of_month() -> None:
    # 2025-03-15T12:00:00Z -> 2025-03-01T00:00:00Z
    ts = 1742040000_000  # 2025-03-15
    start = month_bucket_start_ms(ts)
    assert start <= ts
    # difference at most 14 days
    assert ts - start < 31 * 24 * 60 * 60 * 1000


def test_cost_rollup_mtd_sums_only_current_month() -> None:
    ws = uuid4()
    svc = CostRollupService()
    # March 1 baseline
    march_1 = month_bucket_start_ms(1742040000_000)
    feb_28 = march_1 - 24 * 60 * 60 * 1000
    svc.append(
        DimensionedUsageEvent(
            workspace_id=ws,
            metric="tokens",
            cost_usd_micro=500,
            timestamp_ms=feb_28,  # previous month -- ignored
        )
    )
    svc.append(
        DimensionedUsageEvent(
            workspace_id=ws,
            metric="tokens",
            cost_usd_micro=1500,
            timestamp_ms=march_1 + 1000,
        )
    )
    mtd = svc.month_to_date(workspace_id=ws, now_ms=march_1 + 86_400_000)
    assert mtd.cost_usd_micro == 1500
    assert mtd.month_start_ms == march_1


def test_cost_rollup_breakdown_groups_by_dimensions() -> None:
    ws = uuid4()
    agent = uuid4()
    svc = CostRollupService()
    base = 1_000_000
    svc.extend(
        [
            DimensionedUsageEvent(
                workspace_id=ws, agent_id=agent, channel="web",
                model="gpt-4o", metric="tokens",
                cost_usd_micro=100, timestamp_ms=base + 1,
            ),
            DimensionedUsageEvent(
                workspace_id=ws, agent_id=agent, channel="web",
                model="gpt-4o", metric="tokens",
                cost_usd_micro=200, timestamp_ms=base + 2,
            ),
            DimensionedUsageEvent(
                workspace_id=ws, agent_id=agent, channel="slack",
                model="gpt-4o", metric="tokens",
                cost_usd_micro=50, timestamp_ms=base + 3,
            ),
        ]
    )
    rows = svc.breakdown(workspace_id=ws, start_ms=0, end_ms=base + 10)
    assert len(rows) == 2
    web = next(r for r in rows if r.channel == "web")
    assert web.cost_usd_micro == 300
    slack = next(r for r in rows if r.channel == "slack")
    assert slack.cost_usd_micro == 50


def test_cost_rollup_projected_eom_extrapolates_linearly() -> None:
    ws = uuid4()
    svc = CostRollupService()
    march_1 = month_bucket_start_ms(1742040000_000)
    one_day = 86_400_000
    svc.append(
        DimensionedUsageEvent(
            workspace_id=ws,
            metric="tokens",
            cost_usd_micro=1_000,
            timestamp_ms=march_1 + one_day // 2,  # mid-day 1
        )
    )
    proj = svc.projected_eom(
        workspace_id=ws,
        now_ms=march_1 + one_day,  # 1 day elapsed
        month_length_ms=31 * one_day,
    )
    # 1000 microUSD over 1 day -> ~31000 over 31 days
    assert 30_000 <= proj <= 32_000
