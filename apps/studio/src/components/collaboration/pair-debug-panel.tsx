"use client";

import { useState } from "react";

import {
  eventAtPlayhead,
  setPlayhead,
  type PairDebugSession,
} from "@/lib/collaboration";

import { PresenceBar } from "./presence-bar";

interface PairDebugPanelProps {
  session: PairDebugSession;
  onScrub?(playheadMs: number): void;
}

export function PairDebugPanel(props: PairDebugPanelProps): JSX.Element {
  const { session, onScrub } = props;
  const [current, setCurrent] = useState<PairDebugSession>(session);
  const focused = eventAtPlayhead(current);
  const max = current.trace[current.trace.length - 1]?.offsetMs ?? 0;
  const min = current.trace[0]?.offsetMs ?? 0;
  const hasTrace = current.trace.length > 0;

  function jumpTo(offsetMs: number): void {
    const next = setPlayhead(current, offsetMs);
    setCurrent(next);
    onScrub?.(next.playheadMs);
  }

  return (
    <section
      data-testid="pair-debug"
      aria-labelledby="pair-debug-title"
      className="space-y-3 instrument-panel rounded-2xl p-4"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="pair-debug-title" className="text-sm font-semibold">
          Pair debugging · {current.id}
        </h3>
        <p className="text-xs text-muted-foreground">Shared trace playhead</p>
      </header>
      <PresenceBar users={current.participants} />
      <div className="rounded-md border bg-muted/45 p-3 text-xs">
        {hasTrace ? (
          <>
            <p data-testid="playhead-readout">
              Playhead: <strong>{current.playheadMs}ms</strong>
              {focused ? ` · ${focused.kind} · ${focused.summary}` : ""}
            </p>
            <input
              type="range"
              min={min}
              max={max}
              step={20}
              value={current.playheadMs}
              onChange={(e) => jumpTo(Number(e.target.value))}
              aria-label="Trace playhead"
              data-testid="playhead-scrubber"
              className="mt-2 w-full"
            />
          </>
        ) : (
          <p data-testid="playhead-empty">
            No trace loaded for pair debugging.
          </p>
        )}
      </div>
      <ol className="space-y-1" data-testid="trace-events">
        {current.trace.map((ev) => {
          const active = focused?.id === ev.id;
          return (
            <li
              key={ev.id}
              data-testid={`trace-event-${ev.id}`}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
                active
                  ? "border-info bg-info/10"
                  : "border-border bg-background"
              }`}
            >
              <button
                type="button"
                data-testid={`trace-jump-${ev.id}`}
                onClick={() => jumpTo(ev.offsetMs)}
                className="rounded border bg-background px-1.5 py-0.5 font-mono text-[11px] hover:bg-muted"
              >
                {ev.offsetMs}ms
              </button>
              <span className="rounded-full border bg-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide">
                {ev.kind}
              </span>
              <span className="flex-1 text-foreground">{ev.summary}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
