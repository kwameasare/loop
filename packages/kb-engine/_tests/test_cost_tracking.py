from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane.usage import UsageLedger, aggregate
from loop_kb_engine import (
    METRIC_EMBEDDING_TOKENS,
    METRIC_EMBEDDING_USD_CENTS,
    METRIC_PAGES_CRAWLED,
    DeterministicEmbeddingService,
    Document,
    FixedSizeChunker,
    InMemoryVectorStore,
    KbCostTracker,
    KnowledgeBase,
    SitemapCrawler,
)

SITEMAP_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>
"""


def _fetcher(url: str) -> tuple[int, dict[str, str], str]:
    if url.endswith("robots.txt"):
        return 200, {"content-type": "text/plain"}, "User-agent: *\nAllow: /"
    if url.endswith("sitemap.xml"):
        return 200, {"content-type": "application/xml"}, SITEMAP_XML
    return 200, {"content-type": "text/html"}, "alpha beta gamma delta"


@pytest.mark.asyncio
async def test_end_to_end_kb_ingestion_emits_usage_events() -> None:
    workspace_id = uuid4()
    ledger = UsageLedger()
    tracker = KbCostTracker(
        ledger,
        embedding_usd_cents_per_1k_tokens=100,
        clock_ms=lambda: 1_234,
    )
    crawler = SitemapCrawler(
        "https://example.com",
        fetcher=_fetcher,
        cost_tracker=tracker,
        workspace_id=workspace_id,
    )
    results, stats = crawler.crawl()
    assert stats.fetched == 2

    kb = KnowledgeBase(
        chunker=FixedSizeChunker(chunk_size=1_000, overlap=0),
        embedder=DeterministicEmbeddingService(dimensions=8),
        vector_store=InMemoryVectorStore(),
        cost_tracker=tracker,
    )
    await kb.ingest(
        Document(
            workspace_id=workspace_id,
            title="fixture",
            text=" ".join(result.content for result in results),
        )
    )

    by_metric = {event.metric: event.quantity for event in ledger.events}
    assert by_metric == {
        METRIC_PAGES_CRAWLED: 2,
        METRIC_EMBEDDING_TOKENS: 8,
        METRIC_EMBEDDING_USD_CENTS: 1,
    }
    assert {event.workspace_id for event in ledger.events} == {workspace_id}
    assert {event.timestamp_ms for event in ledger.events} == {1_234}


def test_usage_events_are_isolated_per_workspace() -> None:
    ws_a, ws_b = uuid4(), uuid4()
    ledger = UsageLedger()
    tracker = KbCostTracker(ledger, clock_ms=lambda: 10)

    tracker.record_pages_crawled(workspace_id=ws_a, count=3)
    tracker.record_pages_crawled(workspace_id=ws_b, count=7)

    quantities = {
        event.workspace_id: event.quantity
        for event in ledger.window(start_ms=0, end_ms=20)
        if event.metric == METRIC_PAGES_CRAWLED
    }
    assert quantities == {ws_a: 3, ws_b: 7}


def test_metric_names_match_usage_rollup_contract() -> None:
    ws = uuid4()
    ledger = UsageLedger()
    tracker = KbCostTracker(ledger, clock_ms=lambda: 0)

    tracker.record_pages_crawled(workspace_id=ws, count=1)
    tracker.record_embedding_tokens(workspace_id=ws, tokens=2)
    tracker.record_embedding_usd_cents(workspace_id=ws, cents=3)

    buckets = aggregate(ledger.events)
    assert {(metric, quantity) for (_, metric, _), quantity in buckets.items()} == {
        ("kb.pages_crawled", 1),
        ("kb.embedding_tokens", 2),
        ("kb.embedding_usd_cents", 3),
    }
