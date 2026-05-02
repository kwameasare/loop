"""
S495 – unit tests for SitemapCrawler (incremental, robots.txt-aware).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from loop_kb_engine.crawler import (
    CrawlResult,
    CrawlStats,
    SitemapCrawler,
    _parse_sitemap,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

ROBOTS_ALLOW = "User-agent: *\nAllow: /"
ROBOTS_DISALLOW_ALL = "User-agent: *\nDisallow: /"
ROBOTS_DISALLOW_ADMIN = "User-agent: *\nDisallow: /admin/"

SITEMAP_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc><lastmod>2026-05-01</lastmod></url>
  <url><loc>https://example.com/page2</loc><lastmod>2026-04-01</lastmod></url>
  <url><loc>https://example.com/page3</loc></url>
</urlset>
"""

SITEMAP_INDEX_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-sub.xml</loc><lastmod>2026-05-01</lastmod></sitemap>
</sitemapindex>
"""

PAGE_HTML = "<html><body>hello</body></html>"


def make_fetcher(
    sitemap_body: str = SITEMAP_XML,
    robots_body: str = ROBOTS_ALLOW,
    page_body: str = PAGE_HTML,
    page_status: int = 200,
) -> Any:
    """Return a deterministic fetcher that never makes network calls."""
    def fetcher(url: str) -> tuple[int, dict[str, str], str]:
        if url.endswith("robots.txt"):
            return 200, {"content-type": "text/plain"}, robots_body
        if "sitemap" in url:
            return 200, {"content-type": "application/xml"}, sitemap_body
        return page_status, {"content-type": "text/html", "last-modified": "Wed, 01 May 2026 00:00:00 GMT"}, page_body

    return fetcher


# ---------------------------------------------------------------------------
# 1. _parse_sitemap
# ---------------------------------------------------------------------------

class TestParseSitemap:
    def test_parses_urlset_locs(self) -> None:
        entries = _parse_sitemap(SITEMAP_XML)
        locs = [e[0] for e in entries]
        assert "https://example.com/page1" in locs
        assert "https://example.com/page2" in locs
        assert "https://example.com/page3" in locs

    def test_parses_lastmod_values(self) -> None:
        entries = _parse_sitemap(SITEMAP_XML)
        by_loc = {e[0]: e[1] for e in entries}
        assert by_loc["https://example.com/page1"] == "2026-05-01"
        assert by_loc["https://example.com/page2"] == "2026-04-01"
        assert by_loc["https://example.com/page3"] is None

    def test_parses_sitemap_index(self) -> None:
        entries = _parse_sitemap(SITEMAP_INDEX_XML)
        assert entries[0][0] == "https://example.com/sitemap-sub.xml"

    def test_returns_empty_on_invalid_xml(self) -> None:
        assert _parse_sitemap("not xml") == []


# ---------------------------------------------------------------------------
# 2. SitemapCrawler – full crawl without changed_since
# ---------------------------------------------------------------------------

class TestSitemapCrawlerBasic:
    def test_fetches_all_sitemap_pages(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        results, stats = crawler.crawl()
        assert stats.fetched == 3
        assert stats.errors == 0
        assert all(r.status == 200 for r in results)

    def test_result_contains_content(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        results, _ = crawler.crawl()
        assert all(PAGE_HTML in r.content for r in results)

    def test_result_has_last_modified_header(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        results, _ = crawler.crawl()
        assert all(r.last_modified is not None for r in results)


# ---------------------------------------------------------------------------
# 3. robots.txt compliance
# ---------------------------------------------------------------------------

class TestRobotsCompliance:
    def test_skips_disallowed_urls(self) -> None:
        crawler = SitemapCrawler(
            "https://example.com",
            fetcher=make_fetcher(robots_body=ROBOTS_DISALLOW_ALL),
        )
        results, stats = crawler.crawl()
        assert stats.skipped_robots == 3
        assert stats.fetched == 0
        assert results == []


# ---------------------------------------------------------------------------
# 4. changed_since filtering (incremental)
# ---------------------------------------------------------------------------

class TestChangedSince:
    def test_skips_pages_older_than_cutoff(self) -> None:
        # page1 = 2026-05-01, page2 = 2026-04-01, page3 = no lastmod
        # cutoff = 2026-04-15 → page2 skipped; page1 and page3 fetched
        cutoff = datetime(2026, 4, 15, tzinfo=timezone.utc)
        crawler = SitemapCrawler(
            "https://example.com",
            changed_since=cutoff,
            fetcher=make_fetcher(),
        )
        results, stats = crawler.crawl()
        assert stats.skipped_unchanged == 1      # page2 (2026-04-01 <= cutoff)
        assert stats.fetched == 2                 # page1 + page3
        urls = [r.url for r in results]
        assert "https://example.com/page2" not in urls

    def test_all_pages_skipped_when_none_newer(self) -> None:
        cutoff = datetime(2026, 12, 31, tzinfo=timezone.utc)
        # page3 has no lastmod → still fetched
        crawler = SitemapCrawler(
            "https://example.com",
            changed_since=cutoff,
            fetcher=make_fetcher(),
        )
        results, stats = crawler.crawl()
        assert stats.skipped_unchanged == 2      # page1 + page2
        assert stats.fetched == 1                 # page3 (no lastmod → not filtered)

    def test_no_filter_when_changed_since_is_none(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        _, stats = crawler.crawl()
        assert stats.skipped_unchanged == 0
        assert stats.fetched == 3


# ---------------------------------------------------------------------------
# 5. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_handles_http_errors_gracefully(self) -> None:
        crawler = SitemapCrawler(
            "https://example.com",
            fetcher=make_fetcher(page_status=404),
        )
        results, stats = crawler.crawl()
        assert stats.errors == 3
        assert stats.fetched == 0
        assert all(r.error is not None for r in results)

    def test_handles_sitemap_fetch_failure(self) -> None:
        def bad_fetcher(url: str) -> tuple[int, dict[str, str], str]:
            if "robots.txt" in url:
                return 200, {}, ROBOTS_ALLOW
            return 500, {}, ""

        crawler = SitemapCrawler("https://example.com", fetcher=bad_fetcher)
        results, stats = crawler.crawl()
        assert results == []
        assert stats.total_discovered == 0

    def test_network_error_recorded(self) -> None:
        def network_err_fetcher(url: str) -> tuple[int, dict[str, str], str]:
            if "robots.txt" in url:
                return 200, {}, ROBOTS_ALLOW
            if "sitemap" in url:
                return 200, {}, SITEMAP_XML
            return 0, {}, "connection refused"

        crawler = SitemapCrawler("https://example.com", fetcher=network_err_fetcher)
        results, stats = crawler.crawl()
        assert stats.errors == 3
        assert all(r.error is not None for r in results)


# ---------------------------------------------------------------------------
# 6. max_pages cap
# ---------------------------------------------------------------------------

class TestMaxPagesCap:
    def test_respects_max_pages_limit(self) -> None:
        crawler = SitemapCrawler(
            "https://example.com",
            fetcher=make_fetcher(),
            max_pages=1,
        )
        results, stats = crawler.crawl()
        assert len(results) == 1
        assert stats.fetched == 1


# ---------------------------------------------------------------------------
# 7. CrawlResult fields
# ---------------------------------------------------------------------------

class TestCrawlResultFields:
    def test_result_url_matches_sitemap_loc(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        results, _ = crawler.crawl()
        urls = {r.url for r in results}
        assert "https://example.com/page1" in urls

    def test_result_content_type_captured(self) -> None:
        crawler = SitemapCrawler("https://example.com", fetcher=make_fetcher())
        results, _ = crawler.crawl()
        assert all("text/html" in r.content_type for r in results)
