"""
S495: Incremental URL Crawler — sitemap-aware, robots.txt-compliant,
       fetches only pages changed since a given timestamp.

Design goals:
- Zero heavy dependencies: uses only Python stdlib (urllib, xml.etree, http).
- Pluggable ``fetcher`` callable for easy testing and HTTP mocking.
- Returns ``CrawlResult`` objects for each URL crawled.
- ``SitemapCrawler.crawl()`` drives the full sitemap → fetch → diff pipeline.
"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class CrawlResult:
    """Outcome of fetching a single URL."""

    url: str
    status: int                        # HTTP status code
    content: str = ""                  # decoded body (empty on error)
    content_type: str = ""
    last_modified: str | None = None   # value of Last-Modified header
    error: str | None = None


# Fetcher signature: URL → (status, headers, body_text)
FetcherFn = Callable[[str], tuple[int, dict[str, str], str]]


# ---------------------------------------------------------------------------
# Default HTTP fetcher (stdlib only, no third-party deps)
# ---------------------------------------------------------------------------

_TIMEOUT = 15  # seconds


def _http_fetch(url: str) -> tuple[int, dict[str, str], str]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "LoopKBCrawler/1.0 (sitemap-aware)"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 – controlled URL
            headers = {k.lower(): v for k, v in resp.headers.items()}
            charset = "utf-8"
            ct = headers.get("content-type", "")
            m = re.search(r"charset=([^\s;]+)", ct)
            if m:
                charset = m.group(1)
            body = resp.read().decode(charset, errors="replace")
            return resp.status, headers, body
    except urllib.error.HTTPError as exc:
        return exc.code, {}, ""
    except Exception as exc:  # noqa: BLE001
        return 0, {}, str(exc)


# ---------------------------------------------------------------------------
# Robots.txt parser (cached per host)
# ---------------------------------------------------------------------------

class _RobotsCache:
    def __init__(self, fetcher: FetcherFn) -> None:
        self._fetcher = fetcher
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def is_allowed(self, url: str, user_agent: str = "LoopKBCrawler") -> bool:
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{base}/robots.txt"
            _, _, body = self._fetcher(robots_url)
            rp.parse(body.splitlines())
            self._cache[base] = rp
        return self._cache[base].can_fetch(user_agent, url)


# ---------------------------------------------------------------------------
# Sitemap parser
# ---------------------------------------------------------------------------

_SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def _parse_sitemap(xml_text: str) -> list[tuple[str, str | None]]:
    """
    Return list of (loc, lastmod_or_None) from a sitemap or sitemap-index.

    Handles both sitemapindex (recurse) and urlset.  For simplicity this
    implementation handles sitemapindex entries as plain URLs — the caller
    is responsible for recursive fetching if needed.
    """
    results: list[tuple[str, str | None]] = []
    try:
        root = ET.fromstring(xml_text)  # noqa: S314 — controlled content
    except ET.ParseError:
        return results
    # urlset (most common)
    for url_el in root.findall("sm:url", _SITEMAP_NS):
        loc = url_el.findtext("sm:loc", namespaces=_SITEMAP_NS)
        lastmod = url_el.findtext("sm:lastmod", namespaces=_SITEMAP_NS)
        if loc:
            results.append((loc.strip(), lastmod.strip() if lastmod else None))
    # sitemapindex — add sitemap locs as candidates
    for sm_el in root.findall("sm:sitemap", _SITEMAP_NS):
        loc = sm_el.findtext("sm:loc", namespaces=_SITEMAP_NS)
        lastmod = sm_el.findtext("sm:lastmod", namespaces=_SITEMAP_NS)
        if loc:
            results.append((loc.strip(), lastmod.strip() if lastmod else None))
    return results


# ---------------------------------------------------------------------------
# SitemapCrawler
# ---------------------------------------------------------------------------

@dataclass
class CrawlStats:
    total_discovered: int = 0
    skipped_robots: int = 0
    skipped_unchanged: int = 0
    fetched: int = 0
    errors: int = 0


class SitemapCrawler:
    """
    Crawl a site starting from its ``/sitemap.xml``.

    Parameters
    ----------
    base_url:
        Root URL of the site (scheme + host, e.g. ``https://example.com``).
    changed_since:
        Optional datetime (timezone-aware recommended).  URLs whose
        ``lastmod`` value is **at or before** this timestamp are skipped.
    fetcher:
        Callable ``(url) -> (status, headers, body_text)``.
        Defaults to the stdlib HTTP fetcher.
    sitemap_path:
        Relative path to the sitemap; defaults to ``/sitemap.xml``.
    max_pages:
        Safety cap on the number of pages fetched in one run.
    """

    def __init__(
        self,
        base_url: str,
        *,
        changed_since: datetime | None = None,
        fetcher: FetcherFn = _http_fetch,
        sitemap_path: str = "/sitemap.xml",
        max_pages: int = 500,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.changed_since = changed_since
        self._fetcher = fetcher
        self._sitemap_path = sitemap_path
        self._max_pages = max_pages
        self._robots = _RobotsCache(fetcher)

    # ---------------------------------------------------------------- public

    def crawl(self) -> tuple[list[CrawlResult], CrawlStats]:
        """
        1. Fetch sitemap.
        2. Filter by robots.txt.
        3. Filter by lastmod vs. changed_since.
        4. Fetch each remaining URL (up to max_pages).

        Returns (results, stats).
        """
        stats = CrawlStats()
        sitemap_url = f"{self.base_url}{self._sitemap_path}"
        entries = self._fetch_sitemap(sitemap_url)
        stats.total_discovered = len(entries)

        results: list[CrawlResult] = []
        for url, lastmod in entries:
            if not self._robots.is_allowed(url):
                stats.skipped_robots += 1
                continue
            if self._is_unchanged(lastmod):
                stats.skipped_unchanged += 1
                continue
            result = self._fetch_page(url)
            results.append(result)
            if result.error or result.status >= 400:
                stats.errors += 1
            else:
                stats.fetched += 1
            if stats.fetched >= self._max_pages:
                break

        return results, stats

    # ---------------------------------------------------------------- private

    def _fetch_sitemap(self, url: str) -> list[tuple[str, str | None]]:
        status, _, body = self._fetcher(url)
        if status != 200 or not body:
            return []
        return _parse_sitemap(body)

    def _is_unchanged(self, lastmod: str | None) -> bool:
        if self.changed_since is None or lastmod is None:
            return False
        try:
            dt = datetime.fromisoformat(lastmod)
            # Make timezone-aware if naive (assume UTC).
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            cs = self.changed_since
            if cs.tzinfo is None:
                cs = cs.replace(tzinfo=timezone.utc)
            return dt <= cs
        except ValueError:
            return False

    def _fetch_page(self, url: str) -> CrawlResult:
        status, headers, body = self._fetcher(url)
        if status == 0:
            # Network error — body contains error message.
            return CrawlResult(url=url, status=0, error=body or "network error")
        return CrawlResult(
            url=url,
            status=status,
            content=body if status < 400 else "",
            content_type=headers.get("content-type", ""),
            last_modified=headers.get("last-modified"),
            error=f"HTTP {status}" if status >= 400 else None,
        )
