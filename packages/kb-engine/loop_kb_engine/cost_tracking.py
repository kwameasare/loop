"""UsageEvent emission for KB ingestion and crawl costs."""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from loop_control_plane.usage import UsageEvent

METRIC_PAGES_CRAWLED = "kb.pages_crawled"
METRIC_EMBEDDING_TOKENS = "kb.embedding_tokens"
METRIC_EMBEDDING_USD_CENTS = "kb.embedding_usd_cents"

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class UsageEventSink(Protocol):
    def append(self, event: UsageEvent) -> None: ...


@dataclass(frozen=True)
class KbUsageMetrics:
    pages_crawled: str = METRIC_PAGES_CRAWLED
    embedding_tokens: str = METRIC_EMBEDDING_TOKENS
    embedding_usd_cents: str = METRIC_EMBEDDING_USD_CENTS


DEFAULT_KB_USAGE_METRICS = KbUsageMetrics()


class KbCostTracker:
    def __init__(
        self,
        sink: UsageEventSink,
        *,
        embedding_usd_cents_per_1k_tokens: float = 0.0,
        clock_ms: Callable[[], int] | None = None,
        metrics: KbUsageMetrics = DEFAULT_KB_USAGE_METRICS,
    ) -> None:
        self._sink = sink
        self._embedding_usd_cents_per_1k_tokens = embedding_usd_cents_per_1k_tokens
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.metrics = metrics

    def record_pages_crawled(self, *, workspace_id: UUID, count: int) -> None:
        self._append(workspace_id=workspace_id, metric=self.metrics.pages_crawled, quantity=count)

    def record_embedding_texts(self, *, workspace_id: UUID, texts: list[str]) -> None:
        tokens = estimate_embedding_tokens(texts)
        self.record_embedding_tokens(workspace_id=workspace_id, tokens=tokens)
        self.record_embedding_usd_cents(
            workspace_id=workspace_id,
            cents=self.embedding_usd_cents(tokens),
        )

    def record_embedding_tokens(self, *, workspace_id: UUID, tokens: int) -> None:
        self._append(workspace_id=workspace_id, metric=self.metrics.embedding_tokens, quantity=tokens)

    def record_embedding_usd_cents(self, *, workspace_id: UUID, cents: int) -> None:
        self._append(workspace_id=workspace_id, metric=self.metrics.embedding_usd_cents, quantity=cents)

    def embedding_usd_cents(self, tokens: int) -> int:
        if tokens <= 0 or self._embedding_usd_cents_per_1k_tokens <= 0:
            return 0
        return math.ceil(tokens * self._embedding_usd_cents_per_1k_tokens / 1000)

    def _append(self, *, workspace_id: UUID, metric: str, quantity: int) -> None:
        if quantity < 0:
            raise ValueError("usage quantity must be non-negative")
        self._sink.append(
            UsageEvent(
                workspace_id=workspace_id,
                metric=metric,
                quantity=quantity,
                timestamp_ms=self._clock_ms(),
            )
        )


def estimate_embedding_tokens(texts: list[str]) -> int:
    return sum(len(_TOKEN_RE.findall(text)) for text in texts)


__all__ = [
    "DEFAULT_KB_USAGE_METRICS",
    "METRIC_EMBEDDING_TOKENS",
    "METRIC_EMBEDDING_USD_CENTS",
    "METRIC_PAGES_CRAWLED",
    "KbCostTracker",
    "KbUsageMetrics",
    "UsageEventSink",
    "estimate_embedding_tokens",
]
