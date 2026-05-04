"""Tests for the live model catalog.

Hermetic — no real network. Uses ``httpx.MockTransport`` to drive the
discovery functions and a tmp-path cache for the on-disk layer.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from loop_gateway.model_catalog import (
    FALLBACK_MODELS,
    ModelCatalog,
    ModelInfo,
    classify_tier,
    default_model,
    fetch_anthropic_models,
    fetch_openai_models,
    vendor_for,
)

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "models.json"


@pytest.fixture(autouse=True)
def _reset_module_singleton() -> Iterator[None]:
    """Make sure the module-level ``_DEFAULT_CATALOG`` doesn't leak between tests."""
    import loop_gateway.model_catalog as mc

    saved = mc._DEFAULT_CATALOG
    mc._DEFAULT_CATALOG = None
    yield
    mc._DEFAULT_CATALOG = saved


def _openai_payload(*ids: str) -> dict:
    return {
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": 1_700_000_000 + i,
                "owned_by": "openai",
            }
            for i, model_id in enumerate(ids)
        ]
    }


def _anthropic_payload(*ids: str) -> dict:
    return {
        "data": [
            {
                "type": "model",
                "id": model_id,
                "display_name": model_id.replace("-", " ").title(),
                "created_at": "2024-10-22T00:00:00Z",
            }
            for model_id in ids
        ]
    }


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------- #
# OpenAI discovery                                                            #
# --------------------------------------------------------------------------- #


def test_fetch_openai_models_parses_chat_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json=_openai_payload(
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "text-embedding-3-small", "dall-e-3"
            ),
        )

    with _mock_client(handler) as client:
        models = fetch_openai_models("sk-test", client=client)
    ids = [m.id for m in models]
    # Embedding + image models are filtered out
    assert "text-embedding-3-small" not in ids
    assert "dall-e-3" not in ids
    # Chat models survive
    assert "gpt-4o" in ids
    assert "gpt-4o-mini" in ids
    assert "gpt-4-turbo" in ids
    # Vendor stamped, created_at parsed
    assert all(m.vendor == "openai" for m in models)
    assert all(m.created_at >= 1_700_000_000 for m in models)


def test_fetch_openai_models_keeps_o1_o3_o4_reasoning_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_openai_payload("o1-preview", "o1-mini", "o3", "o4-mini"))

    with _mock_client(handler) as client:
        models = fetch_openai_models("sk-test", client=client)
    ids = {m.id for m in models}
    assert ids == {"o1-preview", "o1-mini", "o3", "o4-mini"}


def test_fetch_openai_models_returns_empty_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    with _mock_client(handler) as client:
        assert fetch_openai_models("sk-bad", client=client) == []


def test_fetch_openai_models_returns_empty_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    with _mock_client(handler) as client:
        assert fetch_openai_models("sk-test", client=client) == []


def test_fetch_openai_models_skips_malformed_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-4o-mini", "created": 1700},
                    {"id": 12345},  # not a string
                    {"object": "model"},  # missing id
                    "not-a-dict",  # bad row
                ]
            },
        )

    with _mock_client(handler) as client:
        models = fetch_openai_models("sk-test", client=client)
    assert [m.id for m in models] == ["gpt-4o-mini"]


# --------------------------------------------------------------------------- #
# Anthropic discovery                                                         #
# --------------------------------------------------------------------------- #


def test_fetch_anthropic_models_parses_iso_timestamp() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers["x-api-key"] == "sk-ant-test"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(
            200,
            json=_anthropic_payload(
                "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"
            ),
        )

    with _mock_client(handler) as client:
        models = fetch_anthropic_models("sk-ant-test", client=client)
    ids = [m.id for m in models]
    assert "claude-3-5-sonnet-20241022" in ids
    assert "claude-3-5-haiku-20241022" in ids
    assert all(m.vendor == "anthropic" for m in models)
    # ISO 8601 → epoch
    assert all(m.created_at > 1_700_000_000 for m in models)


def test_fetch_anthropic_models_filters_non_claude() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "claude-3-5-haiku-latest", "created_at": "2024-10-22T00:00:00Z"},
                    {"id": "computer-use-beta", "created_at": "2024-10-22T00:00:00Z"},
                ]
            },
        )

    with _mock_client(handler) as client:
        models = fetch_anthropic_models("sk-ant", client=client)
    assert [m.id for m in models] == ["claude-3-5-haiku-latest"]


# --------------------------------------------------------------------------- #
# Catalog: in-process + on-disk caching                                       #
# --------------------------------------------------------------------------- #


def test_catalog_caches_in_process_after_first_fetch(cache_path: Path) -> None:
    fetch_openai_calls = []

    def fake_fetch_openai(api_key: str, **_: object) -> list[ModelInfo]:
        fetch_openai_calls.append(api_key)
        return [ModelInfo(id="gpt-4o-mini", vendor="openai", created_at=1700)]

    catalog = ModelCatalog(
        fetch_openai=fake_fetch_openai,
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        first = catalog.list("openai")
        second = catalog.list("openai")
    finally:
        del os.environ["OPENAI_API_KEY"]
    assert first == second
    # Only one call to the fetcher despite two .list()s
    assert len(fetch_openai_calls) == 1


def test_catalog_persists_to_disk_and_reads_back(cache_path: Path) -> None:
    fetch_calls = []

    def fake_fetch_openai(api_key: str, **_: object) -> list[ModelInfo]:
        fetch_calls.append(api_key)
        return [
            ModelInfo(id="gpt-4o-mini-2024-07-18", vendor="openai", created_at=1721260800),
            ModelInfo(id="gpt-4o", vendor="openai", created_at=1721260800),
        ]

    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        # First catalog fetches and writes to disk
        first = ModelCatalog(
            fetch_openai=fake_fetch_openai,
            fetch_anthropic=lambda *_a, **_kw: [],
            cache_path=cache_path,
        )
        first.list("openai")
        assert cache_path.is_file()
        payload = json.loads(cache_path.read_text())
        assert "fetched_at" in payload
        assert any(m["id"].startswith("gpt-4o-mini") for m in payload["models"]["openai"])

        # Second catalog reads from disk — does NOT call fetcher
        second = ModelCatalog(
            fetch_openai=fake_fetch_openai,
            fetch_anthropic=lambda *_a, **_kw: [],
            cache_path=cache_path,
        )
        models = second.list("openai")
        assert len(fetch_calls) == 1  # still just the original fetch
        assert "gpt-4o-mini-2024-07-18" in {m.id for m in models}
    finally:
        del os.environ["OPENAI_API_KEY"]


def test_catalog_disk_cache_expires_after_ttl(cache_path: Path) -> None:
    fetch_calls = []

    def fake_fetch_openai(api_key: str, **_: object) -> list[ModelInfo]:
        fetch_calls.append(api_key)
        return [ModelInfo(id="gpt-4o-mini", vendor="openai", created_at=1700)]

    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        # Write a stale cache (fetched_at way in the past)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "fetched_at": int(time.time()) - 100_000,  # > 24h ago
                    "models": {
                        "openai": [{"id": "stale-model", "created_at": 1, "display_name": ""}],
                        "anthropic": [],
                    },
                }
            )
        )

        catalog = ModelCatalog(
            fetch_openai=fake_fetch_openai,
            fetch_anthropic=lambda *_a, **_kw: [],
            cache_path=cache_path,
            cache_ttl_seconds=86_400,
        )
        models = catalog.list("openai")
    finally:
        del os.environ["OPENAI_API_KEY"]
    # Stale cache rejected; fresh fetch happened
    assert len(fetch_calls) == 1
    assert [m.id for m in models] == ["gpt-4o-mini"]


def test_catalog_skips_fetch_when_no_api_key(cache_path: Path) -> None:
    fetch_calls = []

    def fake_fetch_openai(api_key: str, **_: object) -> list[ModelInfo]:
        fetch_calls.append(api_key)
        return [ModelInfo(id="gpt-4o-mini", vendor="openai")]

    # Make sure neither env var is set
    saved = {k: os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "LOOP_GATEWAY_OPENAI_API_KEY")}
    try:
        catalog = ModelCatalog(
            fetch_openai=fake_fetch_openai,
            fetch_anthropic=lambda *_a, **_kw: [],
            cache_path=cache_path,
        )
        models = catalog.list("openai")
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    assert fetch_calls == []
    assert models == []  # empty list; pick_default will fall through to FALLBACK


# --------------------------------------------------------------------------- #
# pick_default — selection heuristic                                          #
# --------------------------------------------------------------------------- #


def test_pick_default_cheap_prefers_mini_variant(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="gpt-4o", vendor="openai", created_at=1700),
            ModelInfo(id="gpt-4o-mini", vendor="openai", created_at=1700),
            ModelInfo(id="gpt-4-turbo", vendor="openai", created_at=1700),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        assert catalog.pick_default("openai", profile="cheap") == "gpt-4o-mini"
    finally:
        del os.environ["OPENAI_API_KEY"]


def test_pick_default_cheap_prefers_latest_dated_mini(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="gpt-4o-mini-2024-07-18", vendor="openai", created_at=1721260800),
            ModelInfo(id="gpt-4o-mini-2024-12-01", vendor="openai", created_at=1733011200),
            ModelInfo(id="gpt-4o", vendor="openai", created_at=1721260800),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        # The newer dated mini wins
        assert catalog.pick_default("openai", profile="cheap") == "gpt-4o-mini-2024-12-01"
    finally:
        del os.environ["OPENAI_API_KEY"]


def test_pick_default_anthropic_cheap_prefers_haiku_latest_alias(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [],
        fetch_anthropic=lambda *_a, **_kw: [
            ModelInfo(id="claude-3-5-haiku-20241022", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-5-haiku-latest", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-5-sonnet-latest", vendor="anthropic", created_at=1729555200),
        ],
        cache_path=cache_path,
    )
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    try:
        assert catalog.pick_default("anthropic", profile="cheap") == "claude-3-5-haiku-latest"
    finally:
        del os.environ["ANTHROPIC_API_KEY"]


def test_pick_default_balanced_prefers_sonnet(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [],
        fetch_anthropic=lambda *_a, **_kw: [
            ModelInfo(id="claude-3-5-haiku-latest", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-5-sonnet-latest", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-opus-latest", vendor="anthropic", created_at=1729555200),
        ],
        cache_path=cache_path,
    )
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    try:
        assert catalog.pick_default("anthropic", profile="balanced") == "claude-3-5-sonnet-latest"
    finally:
        del os.environ["ANTHROPIC_API_KEY"]


def test_pick_default_best_prefers_opus(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [],
        fetch_anthropic=lambda *_a, **_kw: [
            ModelInfo(id="claude-3-5-haiku-latest", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-5-sonnet-latest", vendor="anthropic", created_at=1729555200),
            ModelInfo(id="claude-3-opus-latest", vendor="anthropic", created_at=1729555200),
        ],
        cache_path=cache_path,
    )
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    try:
        assert catalog.pick_default("anthropic", profile="best") == "claude-3-opus-latest"
    finally:
        del os.environ["ANTHROPIC_API_KEY"]


def test_pick_default_balanced_excludes_pro_tier(cache_path: Path) -> None:
    """Regression: ``-pro`` is the frontier tier (e.g. ``gpt-5.5-pro``),
    not a balanced workhorse. Balanced must never pick a pro-tier id
    when an unmarked workhorse (``gpt-4o``, ``gpt-5-chat-latest``) is
    available."""
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="gpt-4o", vendor="openai", created_at=1721260800),
            ModelInfo(id="gpt-4o-mini", vendor="openai", created_at=1721260800),
            ModelInfo(id="gpt-5-chat-latest", vendor="openai", created_at=1745000000),
            # The frontier id we don't want as the balanced default
            ModelInfo(id="gpt-5.5-pro-2026-04-23", vendor="openai", created_at=1746000000),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        balanced = catalog.pick_default("openai", profile="balanced")
        best = catalog.pick_default("openai", profile="best")
        cheap = catalog.pick_default("openai", profile="cheap")
    finally:
        del os.environ["OPENAI_API_KEY"]
    # Balanced gets the unmarked workhorse, NOT the pro tier
    assert balanced != "gpt-5.5-pro-2026-04-23"
    assert balanced in {"gpt-4o", "gpt-5-chat-latest"}
    # Best gets the pro tier
    assert best == "gpt-5.5-pro-2026-04-23"
    # Cheap gets the mini
    assert cheap == "gpt-4o-mini"


def test_pick_default_best_includes_pro_and_turbo_and_o_series(cache_path: Path) -> None:
    """All three frontier markers (``-pro``, ``-turbo``, o-series prefix)
    should classify as ``best`` and the most recent wins within the tier."""
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="gpt-4-turbo-2024-04-09", vendor="openai", created_at=1712620800),
            ModelInfo(id="o3", vendor="openai", created_at=1738000000),
            ModelInfo(id="gpt-5.5-pro-2026-04-23", vendor="openai", created_at=1745366400),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        # Newest of the three frontier ids wins
        assert catalog.pick_default("openai", profile="best") == "gpt-5.5-pro-2026-04-23"
    finally:
        del os.environ["OPENAI_API_KEY"]


def test_pick_default_o_series_mini_classifies_as_cheap(cache_path: Path) -> None:
    """``o4-mini`` and ``o3-mini`` should classify as cheap despite the
    o-series prefix — the ``-mini`` cheap marker takes precedence."""
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="o3", vendor="openai", created_at=1738000000),
            ModelInfo(id="o3-mini", vendor="openai", created_at=1738000000),
            ModelInfo(id="o4-mini", vendor="openai", created_at=1740000000),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        assert catalog.pick_default("openai", profile="cheap") == "o4-mini"  # newest mini wins
        assert catalog.pick_default("openai", profile="best") == "o3"  # only non-mini frontier
    finally:
        del os.environ["OPENAI_API_KEY"]


def test_pick_default_balanced_falls_back_when_no_balanced_models_in_catalog(
    cache_path: Path,
) -> None:
    """Live catalog has models but none classify as balanced (only mini +
    pro). We must NOT silently down/up-grade — fall through to the
    bundled balanced list instead."""
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [
            ModelInfo(id="gpt-5.4-mini", vendor="openai", created_at=1745000000),
            ModelInfo(id="gpt-5.5-pro-2026-04-23", vendor="openai", created_at=1746000000),
        ],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        result = catalog.pick_default("openai", profile="balanced")
    finally:
        del os.environ["OPENAI_API_KEY"]
    # Bundled balanced list, NOT one of the live models
    assert result == FALLBACK_MODELS["openai"]["balanced"][0]


def test_pick_default_falls_back_when_discovery_returns_empty(cache_path: Path) -> None:
    catalog = ModelCatalog(
        fetch_openai=lambda *_a, **_kw: [],
        fetch_anthropic=lambda *_a, **_kw: [],
        cache_path=cache_path,
    )
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        result = catalog.pick_default("openai", profile="cheap")
    finally:
        del os.environ["OPENAI_API_KEY"]
    assert result == FALLBACK_MODELS["openai"]["cheap"][0]


# --------------------------------------------------------------------------- #
# default_model module-level helper                                           #
# --------------------------------------------------------------------------- #


def test_default_model_honors_pinned_env_override(cache_path: Path) -> None:
    os.environ["LOOP_DP_DEFAULT_MODEL"] = "my-pinned-model"
    try:
        # Pinned override wins regardless of vendor / profile / catalog state
        assert default_model("openai", profile="cheap") == "my-pinned-model"
        assert default_model("anthropic", profile="best") == "my-pinned-model"
    finally:
        del os.environ["LOOP_DP_DEFAULT_MODEL"]


def test_classify_tier_is_mutually_exclusive() -> None:
    """Every well-formed id classifies into exactly one tier — no
    overlap between cheap / balanced / best."""
    assert classify_tier("gpt-5.4-mini") == "cheap"
    assert classify_tier("o4-mini") == "cheap"  # cheap precedence over o-series
    assert classify_tier("claude-haiku-4-5-20251001") == "cheap"

    assert classify_tier("gpt-4o") == "balanced"
    assert classify_tier("gpt-5-chat-latest") == "balanced"
    assert classify_tier("claude-sonnet-4-6") == "balanced"

    assert classify_tier("gpt-5.5-pro-2026-04-23") == "best"
    assert classify_tier("gpt-4-turbo") == "best"
    assert classify_tier("o3") == "best"
    assert classify_tier("claude-opus-4-7") == "best"


def test_vendor_for_recognises_openai_and_anthropic_ids() -> None:
    """Used by ``loop_gateway.cost`` to assign tier-fallback rates to
    discovered-but-uncatalogued models."""
    assert vendor_for("gpt-4o") == "openai"
    assert vendor_for("gpt-5.4-mini") == "openai"
    assert vendor_for("o1-preview") == "openai"
    assert vendor_for("o3-mini") == "openai"
    assert vendor_for("o4") == "openai"
    assert vendor_for("claude-3-5-sonnet-latest") == "anthropic"
    assert vendor_for("claude-haiku-4-5") == "anthropic"

    # Non-supported vendors return None — caller decides what to do
    # (cost.py raises KeyError; runtime maps to LOOP-RT-501).
    assert vendor_for("mistral-large-latest") is None
    assert vendor_for("gemini-1.5-pro") is None
    assert vendor_for("does-not-exist") is None


def test_default_model_uses_fallback_when_nothing_configured(
    cache_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Strip every key the resolver might use
    for k in (
        "LOOP_DP_DEFAULT_MODEL",
        "OPENAI_API_KEY",
        "LOOP_GATEWAY_OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "LOOP_GATEWAY_ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LOOP_GATEWAY_MODEL_CATALOG_PATH", str(cache_path))

    result = default_model("openai", profile="cheap")
    assert result == FALLBACK_MODELS["openai"]["cheap"][0]
