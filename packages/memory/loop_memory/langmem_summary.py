"""LangMem-style episodic summarization (S822)."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from loop_memory.episodic import EpisodicError, auto_summarize

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]{1,}", re.IGNORECASE)
_STOPWORDS = set(re.findall(
    r"[a-z]+",
    "about after again also and because before hello just please thanks that "
    "the their there they this with would",
))
_INTENT_WORDS = set(re.findall(
    r"[a-z]+",
    "account billing blocked deadline error export integration invoice needs "
    "prefers refund region security ticket webhook",
))


class LLMSummaryFn(Protocol):
    def __call__(self, messages: Sequence[str], *, max_chars: int) -> str: ...


class SummaryFn(Protocol):
    def __call__(self, messages: Sequence[str], *, max_chars: int = 240) -> str: ...


@dataclass(frozen=True, slots=True)
class SummaryEvalCase:
    messages: tuple[str, ...]
    query: str


@dataclass(frozen=True, slots=True)
class SummaryRetrievalAblation:
    baseline_score: float
    candidate_score: float
    relative_improvement: float
    passed: bool


def _clean_messages(messages: Sequence[str]) -> list[str]:
    cleaned = [message.strip() for message in messages if message.strip()]
    if not cleaned:
        raise EpisodicError("langmem_summarize requires at least one message")
    return cleaned


def _tokens(text: str) -> list[str]:
    tokens = (token.lower() for token in _TOKEN_RE.findall(text))
    return [token for token in tokens if len(token) > 2 and token not in _STOPWORDS]


def _salient_tokens(lines: Sequence[str], *, limit: int) -> list[str]:
    counts = Counter(token for line in lines for token in _tokens(line))
    ranked = sorted(counts, key=lambda token: (
        -(counts[token] + (2 if token in _INTENT_WORDS else 0)),
        token,
    ),
    )
    return ranked[:limit]


def _score_line(line: str, anchors: set[str]) -> int:
    tokens = set(_tokens(line))
    keyword_bonus = 3 * len(tokens & _INTENT_WORDS)
    anchor_bonus = 2 * len(tokens & anchors)
    entity_bonus = len(re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b|\b[A-Z]{2,}\b", line))
    return keyword_bonus + anchor_bonus + entity_bonus + min(len(tokens), 12)


def _fit(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        raise EpisodicError("max_chars must be positive")
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return text[: max_chars - 3].rstrip() + "..."


def langmem_summarize(
    messages: Sequence[str],
    *,
    max_chars: int = 240,
    llm_summarizer: LLMSummaryFn | None = None,
) -> str:
    lines = _clean_messages(messages)
    anchors = _salient_tokens(lines, limit=12)
    scored = sorted(
        enumerate(lines),
        key=lambda item: (-_score_line(item[1], set(anchors)), item[0]),
    )[:3]
    facts = " ; ".join(line for _, line in scored)
    llm_text = ""
    if llm_summarizer is not None:
        llm_text = llm_summarizer(lines, max_chars=max(48, max_chars // 2)).strip()
    body = llm_text or facts
    cues = ", ".join(anchors[:8])
    if not cues:
        return _fit(body, max_chars)
    cue_text = f"Cues: {cues}"
    body_budget = max(24, max_chars - len(cue_text) - 3)
    return _fit(f"{_fit(body, body_budget)} | {cue_text}", max_chars)


def _query_coverage(summary: str, query: str) -> float:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        raise EpisodicError("summary eval query must contain searchable tokens")
    return len(query_tokens & set(_tokens(summary))) / len(query_tokens)


def evaluate_summary_retrieval(
    cases: Sequence[SummaryEvalCase],
    *,
    summarizer: SummaryFn = langmem_summarize,
    baseline: SummaryFn = auto_summarize,
    max_chars: int = 240,
    min_relative_improvement: float = 0.10,
) -> SummaryRetrievalAblation:
    if not cases:
        raise EpisodicError("summary retrieval eval requires at least one case")
    if min_relative_improvement < 0:
        raise EpisodicError("min_relative_improvement must be >= 0")
    baseline_scores: list[float] = []
    candidate_scores: list[float] = []
    for case in cases:
        baseline_scores.append(
            _query_coverage(baseline(case.messages, max_chars=max_chars), case.query)
        )
        candidate_scores.append(
            _query_coverage(summarizer(case.messages, max_chars=max_chars), case.query)
        )
    baseline_score = sum(baseline_scores) / len(baseline_scores)
    candidate_score = sum(candidate_scores) / len(candidate_scores)
    if baseline_score == 0:
        relative = 1.0 if candidate_score > 0 else 0.0
    else:
        relative = (candidate_score - baseline_score) / baseline_score
    return SummaryRetrievalAblation(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        relative_improvement=relative,
        passed=relative >= min_relative_improvement,
    )
