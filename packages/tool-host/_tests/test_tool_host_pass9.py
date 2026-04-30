"""Pass9 tool-host tests: rate_limit (S722), result_cache (S734), schema_validation (S723)."""

from __future__ import annotations

import pytest
from loop_tool_host.rate_limit import (
    RateLimitConfig,
    TokenBucketLimiter,
    ToolRateLimiter,
    ToolRateLimitExceeded,
)
from loop_tool_host.result_cache import (
    CachePolicy,
    ResultCache,
    canonical_args_key,
)
from loop_tool_host.schema_validation import (
    ToolSchemaError,
    validate,
    validate_args,
    validate_result,
)

# ---- rate_limit (S722) ------------------------------------------------------


def _bucket(now: list[float], capacity: float = 3.0, refill: float = 1.0) -> TokenBucketLimiter:
    return TokenBucketLimiter(
        RateLimitConfig(capacity=capacity, refill_per_second=refill),
        clock=lambda: now[0],
    )


def test_token_bucket_starts_at_capacity() -> None:
    now = [0.0]
    b = _bucket(now)
    assert b.tokens(("k",)) == pytest.approx(3.0)


def test_token_bucket_consumes_then_refills() -> None:
    now = [0.0]
    b = _bucket(now, capacity=3.0, refill=2.0)
    for _ in range(3):
        assert b.try_acquire(("k",)) is True
    assert b.try_acquire(("k",)) is False
    now[0] = 1.0  # 2 tokens refilled
    assert b.try_acquire(("k",)) is True
    assert b.try_acquire(("k",)) is True
    assert b.try_acquire(("k",)) is False


def test_token_bucket_capacity_capped_on_refill() -> None:
    now = [0.0]
    b = _bucket(now, capacity=3.0, refill=10.0)
    now[0] = 100.0  # huge elapsed
    assert b.tokens(("k",)) == pytest.approx(3.0)


def test_token_bucket_acquire_raises_typed_error() -> None:
    now = [0.0]
    b = _bucket(now, capacity=1.0, refill=0.001)
    b.acquire(("k",))
    with pytest.raises(ToolRateLimitExceeded) as exc:
        b.acquire(("k",))
    assert exc.value.code == "LOOP-TH-301"


def test_token_bucket_keys_are_independent() -> None:
    now = [0.0]
    b = _bucket(now, capacity=1.0, refill=0.001)
    b.acquire(("a",))
    b.acquire(("b",))  # separate bucket, still has tokens


def test_rate_limit_config_validates() -> None:
    with pytest.raises(ValueError):
        RateLimitConfig(capacity=0, refill_per_second=1)
    with pytest.raises(ValueError):
        RateLimitConfig(capacity=1, refill_per_second=0)


def test_two_axis_tool_rate_limiter() -> None:
    now = [0.0]
    workspace = TokenBucketLimiter(
        RateLimitConfig(capacity=10, refill_per_second=1),
        clock=lambda: now[0],
    )
    agent = TokenBucketLimiter(
        RateLimitConfig(capacity=2, refill_per_second=1),
        clock=lambda: now[0],
    )
    limiter = ToolRateLimiter(per_workspace=workspace, per_agent=agent)
    limiter.acquire(workspace_id="w", agent_id="a", tool="t")
    limiter.acquire(workspace_id="w", agent_id="a", tool="t")
    # Third call: per-agent is empty, raises.
    with pytest.raises(ToolRateLimitExceeded):
        limiter.acquire(workspace_id="w", agent_id="a", tool="t")
    # A different agent on the same workspace still has its own bucket.
    limiter.acquire(workspace_id="w", agent_id="b", tool="t")


# ---- result_cache (S734) ----------------------------------------------------


def test_canonical_args_key_is_stable_and_order_independent() -> None:
    a = canonical_args_key({"x": 1, "y": 2})
    b = canonical_args_key({"y": 2, "x": 1})
    assert a == b
    c = canonical_args_key({"x": 1, "y": 3})
    assert a != c


def test_result_cache_miss_then_hit() -> None:
    c = ResultCache()
    policy = CachePolicy(cacheable=True, ttl_seconds=60.0)
    args = {"q": "hello"}
    assert c.get(workspace_id="w", tool="t", arguments=args, policy=policy) is None
    assert c.misses == 1
    c.put(workspace_id="w", tool="t", arguments=args, result={"x": 1}, policy=policy)
    assert c.get(workspace_id="w", tool="t", arguments=args, policy=policy) == {"x": 1}
    assert c.hits == 1


def test_result_cache_non_cacheable_is_no_op() -> None:
    c = ResultCache()
    policy = CachePolicy(cacheable=False, ttl_seconds=60.0)
    c.put(workspace_id="w", tool="t", arguments={"a": 1}, result={"x": 1}, policy=policy)
    assert len(c) == 0
    assert c.get(workspace_id="w", tool="t", arguments={"a": 1}, policy=policy) is None
    assert c.misses == 0  # opt-out skipped both branches


def test_result_cache_workspace_isolation() -> None:
    c = ResultCache()
    policy = CachePolicy(cacheable=True, ttl_seconds=60.0)
    c.put(workspace_id="w1", tool="t", arguments={}, result="A", policy=policy)
    assert c.get(workspace_id="w2", tool="t", arguments={}, policy=policy) is None


def test_result_cache_ttl_expiry() -> None:
    now = [0.0]
    c = ResultCache(clock=lambda: now[0])
    policy = CachePolicy(cacheable=True, ttl_seconds=10.0)
    c.put(workspace_id="w", tool="t", arguments={}, result="r", policy=policy)
    now[0] = 5.0
    assert c.get(workspace_id="w", tool="t", arguments={}, policy=policy) == "r"
    now[0] = 100.0
    assert c.get(workspace_id="w", tool="t", arguments={}, policy=policy) is None
    assert len(c) == 0


def test_result_cache_lru_eviction() -> None:
    c = ResultCache(max_entries=2)
    policy = CachePolicy(cacheable=True, ttl_seconds=60.0)
    c.put(workspace_id="w", tool="t", arguments={"k": 1}, result=1, policy=policy)
    c.put(workspace_id="w", tool="t", arguments={"k": 2}, result=2, policy=policy)
    c.put(workspace_id="w", tool="t", arguments={"k": 3}, result=3, policy=policy)
    assert len(c) == 2


def test_result_cache_invalidate_tool() -> None:
    c = ResultCache()
    policy = CachePolicy(cacheable=True, ttl_seconds=60.0)
    c.put(workspace_id="w", tool="t1", arguments={}, result=1, policy=policy)
    c.put(workspace_id="w", tool="t2", arguments={}, result=2, policy=policy)
    c.put(workspace_id="w", tool="t1", arguments={"k": 1}, result=3, policy=policy)
    n = c.invalidate_tool(workspace_id="w", tool="t1")
    assert n == 2
    assert len(c) == 1


def test_cache_policy_validates_ttl() -> None:
    with pytest.raises(ValueError):
        CachePolicy(cacheable=True, ttl_seconds=0)


# ---- schema_validation (S723) -----------------------------------------------


def test_validate_args_object_required_and_extra_props() -> None:
    schema = {
        "type": "object",
        "required": ["q"],
        "properties": {"q": {"type": "string"}},
    }
    validate_args({"q": "ok"}, schema)
    with pytest.raises(ToolSchemaError) as exc:
        validate_args({}, schema)
    assert exc.value.code == "LOOP-TH-002"
    with pytest.raises(ToolSchemaError):
        validate_args({"q": "ok", "extra": 1}, schema)
    with pytest.raises(ToolSchemaError):
        validate_args({"q": 5}, schema)  # wrong type


def test_validate_args_must_be_object() -> None:
    with pytest.raises(ToolSchemaError):
        validate_args([], {"type": "object"})  # type: ignore[arg-type]


def test_validate_string_constraints() -> None:
    schema = {"type": "string", "minLength": 2, "maxLength": 4, "pattern": "^[a-z]+$"}
    validate("abc", schema)
    with pytest.raises(ToolSchemaError):
        validate("a", schema)
    with pytest.raises(ToolSchemaError):
        validate("abcde", schema)
    with pytest.raises(ToolSchemaError):
        validate("Abc", schema)


def test_validate_number_bounds_excludes_bool() -> None:
    schema = {"type": "integer", "minimum": 1, "maximum": 5}
    validate(3, schema)
    with pytest.raises(ToolSchemaError):
        validate(0, schema)
    with pytest.raises(ToolSchemaError):
        validate(6, schema)
    with pytest.raises(ToolSchemaError):
        validate(True, schema)  # bool is not int here


def test_validate_array_items() -> None:
    schema = {"type": "array", "items": {"type": "string"}}
    validate(["a", "b"], schema)
    with pytest.raises(ToolSchemaError):
        validate(["a", 1], schema)


def test_validate_enum() -> None:
    schema = {"enum": ["a", "b", 3]}
    validate("a", schema)
    validate(3, schema)
    with pytest.raises(ToolSchemaError):
        validate("c", schema)


def test_validate_union_type() -> None:
    schema = {"type": ["string", "integer"]}
    validate("x", schema)
    validate(3, schema)
    with pytest.raises(ToolSchemaError):
        validate(3.5, schema)


def test_validate_unsupported_type_raises() -> None:
    with pytest.raises(ToolSchemaError):
        validate("x", {"type": "weird"})


def test_validate_result_uses_result_path() -> None:
    schema = {"type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}}
    validate_result({"x": 1}, schema)
    with pytest.raises(ToolSchemaError) as exc:
        validate_result({}, schema)
    assert "$result" in str(exc.value)
