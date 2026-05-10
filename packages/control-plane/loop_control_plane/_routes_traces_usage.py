"""Trace search + usage rollup routes (P0.4 + P0.7a).

Both surfaces have working service modules (`trace_search.py`,
`usage.py`); only the FastAPI shim was missing.

Routes
======
* ``GET /v1/workspaces/{id}/traces`` — search traces by turn_id /
  conversation_id / agent_id / time-window. Page cursor for deep
  scrolls. Studio's "Traces" tab is the primary consumer.
* ``GET /v1/workspaces/{id}/usage`` — list raw usage events for a
  time window. The nightly rollup job pushes aggregated values to
  billing; this endpoint is the operator + studio "Costs" tab read.

Reads are gated to workspace members; no role gradient (a viewer
needs to see traces + usage).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.authorize import authorize_workspace_access
from loop_control_plane.trace_search import TraceMemoryEvent, TraceQuery

router = APIRouter(prefix="/v1/workspaces", tags=["Telemetry"])
router_traces = APIRouter(prefix="/v1/traces", tags=["Telemetry"])


@router.get("/{workspace_id}/traces")
async def search_traces(
    request: Request,
    workspace_id: UUID,
    turn_id: UUID | None = Query(default=None),
    conversation_id: UUID | None = Query(default=None),
    agent_id: UUID | None = Query(default=None),
    started_at_from: datetime | None = Query(default=None),
    started_at_to: datetime | None = Query(default=None),
    only_errors: bool = Query(default=False),
    page_size: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Search persisted traces. Studio's "Traces" tab is the
    primary consumer."""
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    try:
        query = TraceQuery(
            workspace_id=workspace_id,
            turn_id=turn_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            started_at_from=started_at_from,
            started_at_to=started_at_to,
            only_errors=only_errors,
            page_size=page_size,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await cp.trace_search.run(query)
    return {
        "items": [item.model_dump(mode="json") for item in result.items],
        "next_cursor": result.next_cursor,
    }


def _maybe_uuid(value: str) -> UUID | None:
    if len(value) == 32 and "-" not in value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _memory_span(item: Any, index: int) -> dict[str, Any]:
    event = item.memory_events[index]
    status = "error" if event.kind == "blocked" else "ok"
    name = f"memory.{event.kind}.{event.scope}.{event.key}"
    reason = event.blocked_reason if event.kind == "blocked" else event.reason
    return {
        "span_id": event.source_span_id or f"{item.trace_id}:memory:{index}",
        "parent_span_id": item.trace_id,
        "kind": "memory",
        "name": name,
        "started_at": (item.started_at + timedelta(milliseconds=index + 1)).isoformat(),
        "latency_ms": 0,
        "cost_usd": 0,
        "status": status,
        "attrs": {
            "memory_event": event.kind,
            "memory_scope": event.scope,
            "memory_key": event.key,
            "value_preview": event.value_preview,
            "policy_ref": event.policy_ref,
            "reason": reason,
            "source_trace": event.source_trace,
            "source_trace_missing": not bool(event.source_trace),
            "source_turn_id": str(event.source_turn_id) if event.source_turn_id else "",
            "user_id": event.user_id,
        },
    }


def _preview_memory_value(value: object) -> str:
    rendered = value if isinstance(value, str) else str(value)
    if any(token in rendered.lower() for token in ("secret", "token", "password", "card")):
        return "[redacted secret-like value]"
    return rendered if len(rendered) <= 160 else f"{rendered[:157]}..."


async def _memory_events_for_trace(cp: Any, item: Any) -> tuple[TraceMemoryEvent, ...]:
    events = list(item.memory_events)
    list_by_source = getattr(cp.user_memory_store, "list_by_source", None)
    if list_by_source is None:
        return tuple(events)
    entries = await list_by_source(
        workspace_id=item.workspace_id,
        agent_id=item.agent_id,
        source_trace=item.trace_id,
        source_turn_id=item.turn_id,
    )
    seen = {
        (
            event.kind,
            event.scope,
            event.key,
            event.source_trace,
            str(event.source_turn_id) if event.source_turn_id else "",
            event.source_span_id,
        )
        for event in events
    }
    for entry in sorted(
        entries,
        key=lambda e: (e.updated_at, e.scope.value, e.user_id or "", e.key),
    ):
        event = TraceMemoryEvent(
            kind="write",
            scope=entry.scope.value,
            key=entry.key,
            value_preview=_preview_memory_value(entry.value),
            policy_ref=entry.policy_ref,
            reason=entry.write_reason or "runtime memory write",
            source_trace=entry.source_trace,
            source_turn_id=entry.source_turn_id,
            source_span_id=entry.source_span_id,
            user_id=entry.user_id or "",
        )
        dedupe_key = (
            event.kind,
            event.scope,
            event.key,
            event.source_trace,
            str(event.source_turn_id) if event.source_turn_id else "",
            event.source_span_id,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        events.append(event)
    return tuple(events)


@router_traces.get("/{trace_ref}")
async def get_trace_detail(
    request: Request,
    trace_ref: str,
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Fetch detail for one turn trace.

    The current trace store persists summary rows. Until the span store is
    mounted, this route returns a faithful one-span trace envelope derived from
    the summary so Studio's Trace Theater can navigate from a live trace list
    into a real, authorized detail page instead of falling back to fixtures.
    """

    cp = request.app.state.cp
    trace_turn_id = _maybe_uuid(trace_ref)
    for workspace in await cp.workspaces.list_for_user(caller_sub):
        query = TraceQuery(
            workspace_id=workspace.id,
            turn_id=trace_turn_id,
            page_size=200 if trace_turn_id is None else 1,
        )
        result = await cp.trace_search.run(query)
        matches = [
            item for item in result.items if trace_turn_id is not None or item.trace_id == trace_ref
        ]
        if not matches:
            continue
        item = matches[0]
        memory_events = await _memory_events_for_trace(cp, item)
        detail_item = item.model_copy(update={"memory_events": memory_events})
        status = "error" if item.error else "ok"
        spans = [
            {
                "span_id": item.trace_id,
                "parent_span_id": None,
                "kind": "channel",
                "name": "runtime turn",
                "started_at": item.started_at.isoformat(),
                "latency_ms": item.duration_ms,
                "cost_usd": 0,
                "status": status,
                "attrs": {
                    "turn_id": str(item.turn_id),
                    "conversation_id": str(item.conversation_id),
                    "agent_id": str(item.agent_id),
                    "summary_span_count": item.span_count,
                    "channel_binding_id": item.channel_binding_id,
                },
            },
            *[_memory_span(detail_item, index) for index in range(len(memory_events))],
        ]
        return {
            "trace_id": item.trace_id,
            "turn_id": str(item.turn_id),
            "conversation_id": str(item.conversation_id),
            "agent_id": str(item.agent_id),
            "started_at": item.started_at.isoformat(),
            "duration_ms": item.duration_ms,
            "span_count": len(spans),
            "error": item.error,
            "channel_binding_id": item.channel_binding_id,
            "spans": spans,
        }
    raise HTTPException(status_code=404, detail="trace not found")


@router.get("/{workspace_id}/usage")
async def list_usage(
    request: Request,
    workspace_id: UUID,
    start_ms: int = Query(..., ge=0),
    end_ms: int = Query(..., ge=0),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    """Return raw usage events for a (start_ms, end_ms) window.

    The studio's "Costs" page calls this to surface daily breakdowns;
    aggregation happens client-side because the bucket size is a
    user choice.
    """
    cp = request.app.state.cp
    await authorize_workspace_access(
        workspaces=cp.workspaces,
        workspace_id=workspace_id,
        user_sub=caller_sub,
    )
    if start_ms >= end_ms:
        raise HTTPException(status_code=400, detail="start_ms must be < end_ms")
    events = [
        e
        for e in cp.usage_ledger.window(start_ms=start_ms, end_ms=end_ms)
        if e.workspace_id == workspace_id
    ]
    return {
        "items": [e.model_dump(mode="json") for e in events],
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
    }


__all__ = ["router", "router_traces"]
