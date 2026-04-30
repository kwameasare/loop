"""Email thread correlation (S515).

Email lacks a first-class conversation_id, so we recover it from the
message-headers spec:

* ``Message-ID``       \u2014 unique id of the current message
* ``In-Reply-To``      \u2014 id of the immediate parent
* ``References``       \u2014 space-separated ancestry chain (root last)

A reply is correlated to an existing Loop conversation if any of its
``In-Reply-To`` / ``References`` ids was previously observed for that
workspace. New roots get a fresh conversation. Subject-line ``Re:``
heuristics are intentionally avoided \u2014 they are unreliable across
locales and clients.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID, uuid4

#: Strip surrounding angle brackets and whitespace from header values.
_CLEAN_RE = re.compile(r"^\s*<?(.+?)>?\s*$")
_REFERENCES_RE = re.compile(r"<([^>]+)>")


def normalise_message_id(value: str) -> str:
    """Strip surrounding ``<>`` / whitespace from a Message-Id header.

    Empty / unparseable inputs raise ``ValueError``.
    """
    match = _CLEAN_RE.match(value)
    if not match:
        raise ValueError(f"unparseable message-id: {value!r}")
    out = match.group(1).strip()
    if not out or " " in out or "<" in out or ">" in out:
        raise ValueError(f"unparseable message-id: {value!r}")
    return out


def parse_references(value: str) -> list[str]:
    """Parse a ``References:`` header into ordered ids.

    Per RFC-5322 the header is a space-separated list of ``<id>``
    tokens, root *first*. We preserve order so callers can pick the
    nearest ancestor (last entry).
    """
    if not value:
        return []
    return [m.group(1).strip() for m in _REFERENCES_RE.finditer(value)]


@dataclass(frozen=True, slots=True)
class EmailHeaders:
    """The minimum subset of message-headers correlation needs."""

    message_id: str
    in_reply_to: str | None = None
    references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    conversation_id: UUID
    is_new_thread: bool


@dataclass(slots=True)
class ThreadCorrelator:
    """In-memory message-id -> conversation_id index, per workspace.

    Production wires the same shape against Postgres; the algorithm is
    identical so the unit tests cover both paths.
    """

    _index: dict[tuple[UUID, str], UUID] = field(default_factory=dict)

    def correlate(
        self,
        *,
        workspace_id: UUID,
        headers: EmailHeaders,
    ) -> CorrelationResult:
        msg_id = normalise_message_id(headers.message_id)
        # Walk the most-recent-first chain: in_reply_to wins, then references
        # last-to-first (the closest ancestor is the most informative).
        candidates: list[str] = []
        if headers.in_reply_to:
            candidates.append(normalise_message_id(headers.in_reply_to))
        for ref in reversed(headers.references):
            try:
                candidates.append(normalise_message_id(ref))
            except ValueError:
                continue
        for cand in candidates:
            existing = self._index.get((workspace_id, cand))
            if existing is not None:
                self._index[(workspace_id, msg_id)] = existing
                return CorrelationResult(conversation_id=existing, is_new_thread=False)
        # No ancestor matched -> start a new thread.
        new_id = uuid4()
        self._index[(workspace_id, msg_id)] = new_id
        return CorrelationResult(conversation_id=new_id, is_new_thread=True)

    def known(self, workspace_id: UUID, message_id: str) -> bool:
        return (workspace_id, normalise_message_id(message_id)) in self._index


__all__ = [
    "CorrelationResult",
    "EmailHeaders",
    "ThreadCorrelator",
    "normalise_message_id",
    "parse_references",
]
