"""
S495: Incremental URL Crawler — sitemap-aware, robots.txt-compliant,
       fetches only pages changed since a given timestamp.

Design goals:
- Pluggable ``fetcher`` callable for easy testing and HTTP mocking.
- Returns ``CrawlResult`` objects for each URL crawled.
- ``SitemapCrawler.crawl()`` drives the full sitemap → fetch → diff pipeline.
"""
from __future__ import annotations

import random
import re
import threading
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from loop_kb_engine.cost_tracking import KbCostTracker

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


class KbCrawlError(RuntimeError):
    """Structured crawler rejection used for retry/content-limit failures."""

    def __init__(
        self,
        *,
        url: str,
        reason: str,
        status: int | None = None,
        observed_bytes: int | None = None,
        limit_bytes: int | None = None,
    ) -> None:
        self.url = url
        self.reason = reason
        self.status = status
        self.observed_bytes = observed_bytes
        self.limit_bytes = limit_bytes
        super().__init__(reason)


# Fetcher signature: URL → (status, headers, body_text)
FetcherFn = Callable[[str], tuple[int, dict[str, str], str]]


# ---------------------------------------------------------------------------
# Default HTTP fetcher (stdlib only, no third-party deps)
# ---------------------------------------------------------------------------

_TIMEOUT = 15  # seconds
MAX_CONTENT_BYTES = 50 * 1024 * 1024


def _http_fetch(url: str) -> tuple[int, dict[str, str], str]:
    try:
        req = urllib.request.Request(  # noqa: S310 - controlled crawler URL
            url,
            headers={"User-Agent": "LoopKBCrawler/1.0 (sitemap-aware)"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - controlled URL
            headers = {k.lower(): v for k, v in resp.headers.items()}
            _raise_if_content_length_too_large(url, headers, MAX_CONTENT_BYTES)
            charset = "utf-8"
            ct = headers.get("content-type", "")
            m = re.search(r"charset=([^\s;]+)", ct)
            if m:
                charset = m.group(1)
            raw = resp.read(MAX_CONTENT_BYTES + 1)
            if len(raw) > MAX_CONTENT_BYTES:
                raise KbCrawlError(
                    url=url,
                    reason="content exceeds maximum size",
                    observed_bytes=len(raw),
                    limit_bytes=MAX_CONTENT_BYTES,
                )
            body = raw.decode(charset, errors="replace")
            return resp.status, headers, body
    except KbCrawlError:
        raise
    except urllib.error.HTTPError as exc:
        return exc.code, {}, ""
    except Exception as exc:
        return 0, {}, str(exc)


# ---------------------------------------------------------------------------
# Robots.txt parser (cached per host)
# ---------------------------------------------------------------------------

class _RobotsCache:
    def __init__(
        self,
        fetcher: FetcherFn,
        *,
        ttl_seconds: float,
        max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._fetcher = fetcher
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._cache: OrderedDict[str, tuple[float, urllib.robotparser.RobotFileParser]] = (
            OrderedDict()
        )
        self._lock = threading.Lock()

    def is_allowed(self, url: str, user_agent: str = "LoopKBCrawler") -> bool:
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._get(base)
        return rp.can_fetch(user_agent, url)

    def _get(self, base: str) -> urllib.robotparser.RobotFileParser:
        now = self._clock()
        with self._lock:
            cached = self._cache.get(base)
            if cached is not None and now - cached[0] < self._ttl_seconds:
                self._cache.move_to_end(base)
                return cached[1]
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{base}/robots.txt"
        _, _, body = self._fetcher(robots_url)
        rp.parse(body.splitlines())
        with self._lock:
            self._cache[base] = (now, rp)
            self._cache.move_to_end(base)
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)
        return rp


class _HostLimiter:
    def __init__(self, max_per_host: int) -> None:
        if max_per_host <= 0:
            raise ValueError("max_concurrent_per_host must be positive")
        self._max_per_host = max_per_host
        self._semaphores: dict[str, threading.BoundedSemaphore] = {}
        self._lock = threading.Lock()

    def acquire(self, url: str) -> threading.BoundedSemaphore:
        origin = _origin(url)
        with self._lock:
            semaphore = self._semaphores.setdefault(
                origin,
                threading.BoundedSemaphore(self._max_per_host),
            )
        semaphore.acquire()
        return semaphore


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
        max_concurrent_per_host: int = 2,
        robots_ttl_seconds: float = 60 * 60,
        retry_attempts: int = 3,
        retry_base_delay_seconds: float = 0.25,
        max_content_bytes: int = MAX_CONTENT_BYTES,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        cost_tracker: KbCostTracker | None = None,
        workspace_id: UUID | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.changed_since = changed_since
        self._fetcher = fetcher
        self._sitemap_path = sitemap_path
        self._max_pages = max_pages
        self._retry_attempts = retry_attempts
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._max_content_bytes = max_content_bytes
        self._sleep = sleep
        self._jitter = jitter or (
            lambda: random.uniform(0.0, retry_base_delay_seconds)  # noqa: S311
        )
        self._host_limiter = _HostLimiter(max_concurrent_per_host)
        self._robots = _RobotsCache(
            self._fetch_with_retry,
            ttl_seconds=robots_ttl_seconds,
            clock=clock,
        )
        self._cost_tracker = cost_tracker
        self._workspace_id = workspace_id

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

        if self._cost_tracker is not None and self._workspace_id is not None:
            self._cost_tracker.record_pages_crawled(
                workspace_id=self._workspace_id,
                count=stats.fetched,
            )
        return results, stats

    # ---------------------------------------------------------------- private

    def _fetch_sitemap(self, url: str) -> list[tuple[str, str | None]]:
        try:
            status, _, body = self._fetch_with_retry(url)
        except KbCrawlError:
            return []
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
                dt = dt.replace(tzinfo=UTC)
            cs = self.changed_since
            if cs.tzinfo is None:
                cs = cs.replace(tzinfo=UTC)
            return dt <= cs
        except ValueError:
            return False

    def _fetch_page(self, url: str) -> CrawlResult:
        try:
            status, headers, body = self._fetch_with_retry(url)
        except KbCrawlError as exc:
            return CrawlResult(url=url, status=exc.status or 0, error=exc.reason)
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

    def _fetch_with_retry(self, url: str) -> tuple[int, dict[str, str], str]:
        final_error: KbCrawlError | None = None
        for attempt in range(1, self._retry_attempts + 1):
            last_error: KbCrawlError | None = None
            semaphore = self._host_limiter.acquire(url)
            try:
                status, headers, body = self._fetcher(url)
            except (ConnectionResetError, TimeoutError, OSError) as exc:
                last_error = KbCrawlError(url=url, reason=str(exc) or "connection reset")
            finally:
                semaphore.release()
            if last_error is None:
                headers = {k.lower(): v for k, v in headers.items()}
                _raise_if_content_length_too_large(url, headers, self._max_content_bytes)
                observed = len(body.encode())
                if observed > self._max_content_bytes:
                    raise KbCrawlError(
                        url=url,
                        reason="content exceeds maximum size",
                        status=status,
                        observed_bytes=observed,
                        limit_bytes=self._max_content_bytes,
                    )
                if status < 500:
                    return status, headers, body
                last_error = KbCrawlError(url=url, reason=f"HTTP {status}", status=status)
            final_error = last_error
            if attempt < self._retry_attempts:
                delay = self._retry_base_delay_seconds * (2 ** (attempt - 1)) + self._jitter()
                self._sleep(delay)
        assert final_error is not None
        raise final_error


def _origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _raise_if_content_length_too_large(
    url: str,
    headers: dict[str, str],
    limit_bytes: int,
) -> None:
    raw_length = headers.get("content-length")
    if raw_length is None:
        return
    try:
        observed = int(raw_length)
    except ValueError:
        return
    if observed > limit_bytes:
        raise KbCrawlError(
            url=url,
            reason="content exceeds maximum size",
            observed_bytes=observed,
            limit_bytes=limit_bytes,
        )
