"""Pass9 gateway tests: byo_keys (S708), cost_decimal (S713), semantic_cache (S707)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from loop_gateway.byo_keys import (
    BYOKeyMissing,
    InMemoryWorkspaceKeyStore,
    Vendor,
    WorkspaceKeyResolver,
    vendor_for_model,
)
from loop_gateway.cost_decimal import (
    COST_QUANTUM,
    cost_for_decimal,
    sum_costs,
    to_invoice_amount,
    with_markup_decimal,
)
from loop_gateway.semantic_cache import SemanticCache, cosine

# ---- byo_keys (S708) -------------------------------------------------------


def test_vendor_for_model_known_prefixes() -> None:
    assert vendor_for_model("gpt-4o-mini") is Vendor.OPENAI
    assert vendor_for_model("o3-pro") is Vendor.OPENAI
    assert vendor_for_model("claude-3-5-haiku") is Vendor.ANTHROPIC
    assert vendor_for_model("voyage-3") is Vendor.VOYAGE
    assert vendor_for_model("rerank-v3.5") is Vendor.COHERE
    assert vendor_for_model("gemini-2.5-pro") is Vendor.GOOGLE


def test_vendor_for_model_unknown_raises() -> None:
    with pytest.raises(KeyError):
        vendor_for_model("custom-llama")


def test_resolver_prefers_per_model_key() -> None:
    ws = uuid4()
    store = InMemoryWorkspaceKeyStore()
    store.set_model_key(ws, "gpt-4o-mini", "sk-model")
    store.set_vendor_key(ws, Vendor.OPENAI, "sk-vendor")
    r = WorkspaceKeyResolver(store, platform_defaults={Vendor.OPENAI: "sk-default"})
    out = r.resolve(workspace_id=ws, model="gpt-4o-mini")
    assert out.api_key == "sk-model"
    assert out.source == "workspace_model"


def test_resolver_falls_back_to_vendor_then_default() -> None:
    ws = uuid4()
    store = InMemoryWorkspaceKeyStore()
    store.set_vendor_key(ws, Vendor.OPENAI, "sk-vendor")
    r = WorkspaceKeyResolver(store, platform_defaults={Vendor.OPENAI: "sk-default"})
    out = r.resolve(workspace_id=ws, model="gpt-4o-mini")
    assert out.source == "workspace_vendor"
    assert out.api_key == "sk-vendor"

    ws2 = uuid4()
    store2 = InMemoryWorkspaceKeyStore()
    r2 = WorkspaceKeyResolver(store2, platform_defaults={Vendor.OPENAI: "sk-default"})
    out2 = r2.resolve(workspace_id=ws2, model="gpt-4o-mini")
    assert out2.source == "platform_default"
    assert out2.api_key == "sk-default"


def test_resolver_require_byo_blocks_default() -> None:
    ws = uuid4()
    store = InMemoryWorkspaceKeyStore()
    r = WorkspaceKeyResolver(
        store,
        platform_defaults={Vendor.OPENAI: "sk-default"},
        require_byo=True,
    )
    with pytest.raises(BYOKeyMissing):
        r.resolve(workspace_id=ws, model="gpt-4o-mini")


def test_resolver_unknown_vendor_with_no_default_raises() -> None:
    ws = uuid4()
    store = InMemoryWorkspaceKeyStore()
    r = WorkspaceKeyResolver(store)
    with pytest.raises(BYOKeyMissing):
        r.resolve(workspace_id=ws, model="custom-llama")


def test_resolver_does_not_cross_workspaces() -> None:
    ws_a = uuid4()
    ws_b = uuid4()
    store = InMemoryWorkspaceKeyStore()
    store.set_model_key(ws_a, "gpt-4o-mini", "sk-A")
    r = WorkspaceKeyResolver(store)
    with pytest.raises(BYOKeyMissing):
        r.resolve(workspace_id=ws_b, model="gpt-4o-mini")


# ---- cost_decimal (S713) ---------------------------------------------------


def test_cost_for_decimal_quantises_and_zero_in_zero_out() -> None:
    out = cost_for_decimal("gpt-4o-mini", 0, 0)
    assert out == Decimal(0)
    assert out.as_tuple().exponent == COST_QUANTUM.as_tuple().exponent


def test_cost_for_decimal_negative_rejected() -> None:
    with pytest.raises(ValueError):
        cost_for_decimal("gpt-4o-mini", -1, 0)


def test_cost_for_decimal_unknown_model() -> None:
    with pytest.raises(KeyError):
        cost_for_decimal("nope", 1, 1)


def test_with_markup_decimal_round_half_even_no_drift() -> None:
    base = Decimal("0.0000001")
    # 50% markup → still quantised to 0.0000001.
    out = with_markup_decimal(base, 50.0)
    assert out.as_tuple().exponent == COST_QUANTUM.as_tuple().exponent
    assert out >= base


def test_with_markup_decimal_negative_rejected() -> None:
    with pytest.raises(ValueError):
        with_markup_decimal(Decimal("-0.1"), 10.0)
    with pytest.raises(ValueError):
        with_markup_decimal(Decimal("0.1"), -1.0)


def test_sum_costs_no_float_drift() -> None:
    """Sum of 1000 identical small costs is exact."""
    one = Decimal("0.0000001")
    total = sum_costs([one] * 1000)
    assert total == Decimal("0.0001000")


def test_to_invoice_amount_two_decimal_places() -> None:
    assert to_invoice_amount(Decimal("0.12345")) == Decimal("0.12")
    assert to_invoice_amount(Decimal("0.125")) == Decimal("0.12")  # bankers' rounding
    assert to_invoice_amount(Decimal("0.135")) == Decimal("0.14")


# ---- semantic_cache (S707) -------------------------------------------------


def test_cosine_orthogonal_zero_identical_one() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_dim_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


@pytest.mark.asyncio
async def test_semantic_cache_miss_then_hit_above_threshold() -> None:
    table = {"hi": [1.0, 0.0], "hello": [0.99, 0.14]}

    async def embed(text: str) -> list[float]:
        return list(table.get(text, [0.0, 1.0]))

    c = SemanticCache(embed, threshold=0.97)
    assert await c.lookup(workspace_id="w", prompt="hi") is None
    await c.store(workspace_id="w", prompt="hi", response="howdy")
    hit = await c.lookup(workspace_id="w", prompt="hello")
    assert hit is not None
    assert hit.response == "howdy"
    assert hit.similarity >= 0.97


@pytest.mark.asyncio
async def test_semantic_cache_below_threshold_returns_none() -> None:
    table = {"a": [1.0, 0.0], "b": [0.5, 0.866]}  # cosine ≈ 0.5

    async def embed(text: str) -> list[float]:
        return list(table[text])

    c = SemanticCache(embed, threshold=0.97)
    await c.store(workspace_id="w", prompt="a", response="r")
    hit = await c.lookup(workspace_id="w", prompt="b")
    assert hit is None


@pytest.mark.asyncio
async def test_semantic_cache_workspace_isolated() -> None:
    async def embed(text: str) -> list[float]:
        return [1.0, 0.0]

    c = SemanticCache(embed)
    await c.store(workspace_id="w1", prompt="x", response="r1")
    assert await c.lookup(workspace_id="w2", prompt="x") is None
    assert (await c.lookup(workspace_id="w1", prompt="x")).response == "r1"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_semantic_cache_ttl_eviction() -> None:
    async def embed(text: str) -> list[float]:
        return [1.0, 0.0]

    now = [0.0]

    def clock() -> float:
        return now[0]

    c = SemanticCache(embed, ttl_seconds=10.0, clock=clock)
    await c.store(workspace_id="w", prompt="x", response="r")
    now[0] = 5.0
    assert (await c.lookup(workspace_id="w", prompt="x")) is not None
    now[0] = 11.0
    assert (await c.lookup(workspace_id="w", prompt="x")) is None
    assert c.size("w") == 0


@pytest.mark.asyncio
async def test_semantic_cache_lru_bounded() -> None:
    async def embed(text: str) -> list[float]:
        return [1.0, 0.0] if text == "a" else [0.0, 1.0]

    c = SemanticCache(embed, max_entries=2)
    await c.store(workspace_id="w", prompt="a", response="r1")
    await c.store(workspace_id="w", prompt="b", response="r2")
    await c.store(workspace_id="w", prompt="c", response="r3")
    assert c.size("w") == 2


def test_semantic_cache_validates_construction() -> None:
    async def embed(_: str) -> list[float]:
        return [0.0]

    with pytest.raises(ValueError):
        SemanticCache(embed, threshold=0.0)
    with pytest.raises(ValueError):
        SemanticCache(embed, ttl_seconds=0.0)
    with pytest.raises(ValueError):
        SemanticCache(embed, max_entries=0)
