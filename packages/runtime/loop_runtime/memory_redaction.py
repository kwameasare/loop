"""PII redaction for memory writes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

MemoryRedactionMode = Literal["off", "regex", "presidio", "llm_classifier"]

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?\d[\d .()/-]{7,}\d)\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


@dataclass(frozen=True)
class PIISpan:
    start: int
    end: int
    label: str


class MemoryPIIRedactor:
    def __init__(
        self,
        *,
        presidio_analyzer: Any | None = None,
        llm_classifier: Any | None = None,
    ) -> None:
        self._presidio = presidio_analyzer
        self._llm = llm_classifier

    def redact(self, value: Any, *, mode: MemoryRedactionMode) -> Any:
        if mode == "off":
            return value
        if isinstance(value, str):
            return self._redact_text(value, mode=mode)
        if isinstance(value, Mapping):
            mapping = cast(Mapping[str, Any], value)
            return {key: self.redact(item, mode=mode) for key, item in mapping.items()}
        if isinstance(value, list):
            return [self.redact(item, mode=mode) for item in cast(list[Any], value)]
        return value

    def _redact_text(self, text: str, *, mode: MemoryRedactionMode) -> str:
        spans = self._spans(text, mode=mode)
        out = text
        for span in sorted(spans, key=lambda item: item.start, reverse=True):
            if span.start < span.end <= len(out):
                out = f"{out[: span.start]}[{span.label}_REDACTED]{out[span.end :]}"
        return out

    def _spans(self, text: str, *, mode: MemoryRedactionMode) -> tuple[PIISpan, ...]:
        if mode == "regex":
            return _regex_spans(text)
        if mode == "presidio":
            if self._presidio is None:
                return _regex_spans(text)
            results = self._presidio.analyze(
                text=text,
                entities=("EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"),
                language="en",
            )
            return tuple(PIISpan(r.start, r.end, r.entity_type) for r in results)
        if mode == "llm_classifier":
            return (
                tuple(self._llm.classify_pii(text)) if self._llm is not None else _regex_spans(text)
            )
        raise ValueError(f"unsupported memory redaction mode: {mode}")


def _regex_spans(text: str) -> tuple[PIISpan, ...]:
    spans: list[PIISpan] = []
    for label, pattern in (
        ("EMAIL", EMAIL_RE),
        ("PHONE", PHONE_RE),
        ("PAYMENT_CARD", CARD_RE),
    ):
        spans.extend(PIISpan(match.start(), match.end(), label) for match in pattern.finditer(text))
    return tuple(spans)
