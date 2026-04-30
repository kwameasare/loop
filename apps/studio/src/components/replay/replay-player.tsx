"use client";

import { useMemo, useState } from "react";

import {
  type Bubble,
  type ReplayEvent,
  type ReplayTrace,
  nextBoundary,
  previousBoundary,
  snapshotAt,
} from "@/lib/replay";

const ROLE_BADGE: Record<Bubble["role"], string> = {
  user: "bg-sky-100 text-sky-900",
  agent: "bg-emerald-100 text-emerald-900",
  tool: "bg-amber-100 text-amber-900",
  system: "bg-zinc-100 text-zinc-700",
};

function formatTimestamp(ms: number): string {
  return new Date(ms).toISOString().slice(11, 23);
}

function describeEvent(event: ReplayEvent): string {
  switch (event.kind) {
    case "user_message":
      return "User message";
    case "agent_token":
      return "Agent token";
    case "agent_message":
      return "Agent message";
    case "tool_call_start":
      return "Tool call started";
    case "tool_call_end":
      return "Tool call finished";
    case "handoff":
      return "Handoff";
    case "error":
      return "Error";
  }
}

/**
 * Replay / time-travel debugger.
 *
 * Lets the operator scrub through a recorded conversation
 * step-by-step. The transcript on the left re-renders for the
 * cursor's prefix; the right rail shows the active event detail.
 */
export function ReplayPlayer({ trace }: { trace: ReplayTrace }) {
  const [cursor, setCursor] = useState(0);
  const last = trace.events.length - 1;

  const snapshot = useMemo(() => snapshotAt(trace, cursor), [trace, cursor]);

  const onPrev = () => setCursor(previousBoundary(trace, cursor));
  const onNext = () => setCursor(nextBoundary(trace, cursor));
  const onFirst = () => setCursor(0);
  const onLast = () => setCursor(last);

  return (
    <div
      className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]"
      data-testid="replay-player"
    >
      <div className="space-y-3">
        <div
          className="space-y-2"
          role="list"
          aria-label="replay transcript"
        >
          {snapshot.bubbles.length === 0 && (
            <p className="text-muted-foreground text-sm">
              Empty replay -- nothing to show yet.
            </p>
          )}
          {snapshot.bubbles.map((b) => (
            <div
              key={`${b.source_step}-${b.role}`}
              role="listitem"
              data-testid="replay-bubble"
              data-role={b.role}
              className="rounded-md border bg-white p-3 shadow-sm"
            >
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${ROLE_BADGE[b.role]}`}
                >
                  {b.role}
                </span>
                <span className="text-muted-foreground text-xs">
                  {b.actor}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-sm">{b.text}</p>
            </div>
          ))}
        </div>

        <div className="bg-muted/40 sticky bottom-0 flex items-center gap-3 rounded-md border p-3">
          <button
            type="button"
            onClick={onFirst}
            data-testid="replay-first"
            className="rounded border px-2 py-1 text-xs hover:bg-zinc-50"
            aria-label="Jump to first step"
          >
            «
          </button>
          <button
            type="button"
            onClick={onPrev}
            data-testid="replay-prev"
            className="rounded border px-2 py-1 text-xs hover:bg-zinc-50"
            aria-label="Previous boundary"
          >
            ‹
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, last)}
            value={snapshot.cursor}
            onChange={(e) => setCursor(Number(e.target.value))}
            data-testid="replay-scrubber"
            aria-label="Replay cursor"
            className="flex-1"
          />
          <button
            type="button"
            onClick={onNext}
            data-testid="replay-next"
            className="rounded border px-2 py-1 text-xs hover:bg-zinc-50"
            aria-label="Next boundary"
          >
            ›
          </button>
          <button
            type="button"
            onClick={onLast}
            data-testid="replay-last"
            className="rounded border px-2 py-1 text-xs hover:bg-zinc-50"
            aria-label="Jump to last step"
          >
            »
          </button>
          <span
            className="text-muted-foreground tabular-nums text-xs"
            data-testid="replay-cursor"
          >
            {snapshot.cursor + 1} / {trace.events.length}
          </span>
        </div>
      </div>

      <aside
        className="space-y-2 rounded-md border bg-white p-4 text-sm shadow-sm"
        data-testid="replay-event-detail"
      >
        {snapshot.current === null ? (
          <p className="text-muted-foreground">No event selected.</p>
        ) : (
          <>
            <h3 className="text-base font-semibold">
              {describeEvent(snapshot.current)}
            </h3>
            <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted-foreground">step</dt>
              <dd className="tabular-nums">{snapshot.current.step}</dd>
              <dt className="text-muted-foreground">when</dt>
              <dd className="tabular-nums">
                {formatTimestamp(snapshot.current.timestamp_ms)}
              </dd>
              <dt className="text-muted-foreground">actor</dt>
              <dd>{snapshot.current.actor}</dd>
            </dl>
            {snapshot.current.text.length > 0 && (
              <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-zinc-50 p-2 text-xs">
                {snapshot.current.text}
              </pre>
            )}
            {snapshot.current.attributes &&
              Object.keys(snapshot.current.attributes).length > 0 && (
                <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
                  {Object.entries(snapshot.current.attributes).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd className="font-mono">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              )}
          </>
        )}
      </aside>
    </div>
  );
}
