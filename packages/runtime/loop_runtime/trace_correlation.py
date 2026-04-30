"""Cross-agent trace correlation (S408).

In a multi-agent run the parent OTEL span and each child span live
in different services (the parent in the orchestrator, children in
their own runtime processes). To draw a single trace in Tempo /
Honeycomb we have to link them.

OpenTelemetry calls these ``span links`` — a span can declare it
was *caused by* another span even when they are not parent/child
in the local trace. This module formalises the metadata payload
the runtime puts on a child span so consumers can stitch the
multi-agent trace.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MultiAgentTrace",
    "SpanLink",
    "SpanLinkKind",
    "SpanLinker",
    "TraceContext",
]


class SpanLinkKind(StrEnum):
    PARENT_TURN = "parent_turn"
    """Child agent run forked from a parent agent's turn."""
    SIBLING_TURN = "sibling_turn"
    """Sibling child run that shares a parent."""
    SUB_TOOL = "sub_tool"
    """A tool call that internally produced its own span."""


def _validate_hex(value: str, *, length: int) -> str:
    if len(value) != length:
        raise ValueError(f"expected hex of length {length}, got {len(value)}")
    int(value, 16)  # raises if non-hex
    return value


class TraceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    trace_id: str = Field(min_length=32, max_length=32)
    """W3C 16-byte trace id, 32 hex chars."""
    span_id: str = Field(min_length=16, max_length=16)
    """W3C 8-byte span id, 16 hex chars."""
    trace_flags: int = Field(ge=0, le=255, default=1)

    def model_post_init(self, _ctx: Any) -> None:
        _validate_hex(self.trace_id, length=32)
        _validate_hex(self.span_id, length=16)


class SpanLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: SpanLinkKind
    parent: TraceContext
    child: TraceContext

    def to_otel_attrs(self) -> dict[str, str]:
        """Render the link as flat attributes the OTEL exporter accepts."""
        return {
            "loop.link.kind": str(self.kind.value),
            "loop.link.parent.trace_id": self.parent.trace_id,
            "loop.link.parent.span_id": self.parent.span_id,
            "loop.link.child.trace_id": self.child.trace_id,
            "loop.link.child.span_id": self.child.span_id,
        }


class SpanLinker:
    """Build :class:`SpanLink` records from OTEL contexts."""

    @staticmethod
    def link_child(
        *, parent: TraceContext, child: TraceContext, kind: SpanLinkKind
    ) -> SpanLink:
        if parent.trace_id == child.trace_id and parent.span_id == child.span_id:
            raise ValueError("cannot link a span to itself")
        return SpanLink(kind=kind, parent=parent, child=child)


class MultiAgentTrace(BaseModel):
    """Aggregate of all links collected during a multi-agent run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    root: TraceContext
    links: tuple[SpanLink, ...]

    def child_trace_ids(self) -> tuple[str, ...]:
        return tuple(sorted({link.child.trace_id for link in self.links}))

    @classmethod
    def build(
        cls, *, root: TraceContext, links: Iterable[SpanLink]
    ) -> MultiAgentTrace:
        ls = tuple(links)
        return cls(root=root, links=ls)
